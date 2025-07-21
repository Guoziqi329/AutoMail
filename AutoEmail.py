from email.header import decode_header
import email
import re
import ssl
import base64
import quopri
import logging
from database_tools.oracleDatabase import OracleDatabase
import cx_Oracle
from datetime import datetime, timedelta
import asyncio
import aioimaplib

# 配置日志记录器
logging.basicConfig(
    level=logging.INFO,
    handlers=[logging.StreamHandler()]  # 输出到控制台
)


def decode_payload(payload, encoding):
    if encoding == 'base64':
        payload = bytes(payload, 'utf-8')
        base64decode = base64.b64decode(payload)
        return base64decode
    elif encoding == 'quoted-printable':
        check = quopri.decodestring(payload)
        if type(check) is bytes:
            return check.decode('utf-8')
        else:
            return check
    else:
        return payload


def fileNameBase64Decode(name):
    if name is None:
        return None
    if isinstance(name, bytes):
        return name.decode('GBK')

    decode_head = decode_header(name)[0]
    if decode_head[1] is None:
        return name
    name = decode_head[0].decode(decode_head[1] or 'utf-8')
    return name


def get_attachment_filename(disposition):
    matches = re.findall(r'filename="([^"]+)"', disposition)
    return matches[0] if matches else None


def text_processing(body):
    pass


def html_processing(body):
    pass


def image_processing(payload, filename, content_type, base_path):
    pass


def convert_email_time_format(time_str):
    if time_str is None:
        return None
    try:
        time_str = time_str.split('(')[0]
        time_str = time_str.strip()

        # 原始时间格式
        original_format = "%a, %d %b %Y %H:%M:%S %z"
        dt = datetime.strptime(time_str, original_format)

        return dt
    except Exception as e:
        logging.error(f"{e}", exc_info=True)
        return None


def convert_file_time_format(time_str):
    if time_str is None:
        return None
    try:
        original_format = "%Y-%m-%d %H:%M:%S"
        dt = datetime.strptime(time_str, original_format)
        return dt
    except Exception as e:
        logging.error(f"{e}", exc_info=True)


def file_processing(payload, filename, content_disposition, database, power_outage_account_table,
                    power_outage_account_table_columns):
    if not filename:
        filename = get_attachment_filename(content_disposition)

    if filename.split('.')[-1] != 'txt' or '断电账号' not in filename:
        return False

    payload = bytes(payload, "utf-8")
    payload = base64.b64decode(payload).decode()
    payloadList = payload.split('\n')[1:]
    payloadList = [(convert_file_time_format(item.strip('\r').split('\t')[0]), item.strip('\r').split('\t')[1])
                   for item in payloadList if item != '']

    database.clear_table(power_outage_account_table)
    success = database.insert_many(power_outage_account_table, columns=power_outage_account_table_columns, values=payloadList)
    if success is False:
        raise ValueError("database insertion failed")



def process_part(part, database, power_outage_account_table, power_outage_account_table_columns,
                 base_path="./attachments"):
    content_type = part.get_content_type()
    content_disposition = str(part.get("Content-Disposition"))
    filename = fileNameBase64Decode(part.get_filename())

    logging.info(
        f"part Details : Content-Type: {content_type}, Content-Disposition: {content_disposition}, Filename: {filename}")

    payload = part.get_payload(decode=False)

    if isinstance(payload, list):
        logging.info("Payload is a list, processing each sub-part separately.")
        for sub_part in payload:
            process_part(sub_part, database, power_outage_account_table, power_outage_account_table_columns, base_path)
    else:
        if payload is None:
            logging.info("Payload is None, skipping this part.")
            return None

        try:
            contentEncoding = part["Content-Transfer-Encoding"]
            if 'application/octet-stream' not in content_type and "multipart" not in content_disposition:
                body = decode_payload(payload, contentEncoding)
        except Exception as e:
            logging.error(f"{e}")
            return None

        # 邮件部分判断并处理

        # 文本部分处理
        if content_type == "text/plain" and "attachment" not in content_disposition:
            text_processing(body)

        # HTML部分处理
        elif content_type == "text/html" and "attachment" not in content_disposition:
            html_processing(body)

        # 图片处理
        elif "image" in content_type:
            image_processing(payload, filename, content_type, base_path)

        # 文件处理
        elif ("attachment" in content_disposition or "multipart" in content_disposition) and (
                filename or get_attachment_filename(content_disposition)):
            file_processing(payload, filename, content_disposition, database, power_outage_account_table,
                            power_outage_account_table_columns)

        else:
            logging.warning("Unknown content type or disposition, skipping this part.")


async def header_selection(imap, mail_ids, database, email_management_table, email_management_table_columns):
    header_list = list()

    for mail_id in mail_ids:
        try:
            header_data = await imap.fetch(mail_id, '(RFC822.HEADER)')
            status = header_data[0]
            header_data = header_data[1][1]

            # 解析消息
            msg = email.message_from_bytes(header_data)
            # 解码主题
            subject = fileNameBase64Decode(msg.get("subject", None))
            # 解码发件人
            From = msg.get("from", None)
            # 解码接收时间
            ReceivedTime = convert_email_time_format(msg.get("Date", None))

            if status != 'OK':
                logging.error(f"Failed to request email title {mail_id}")
                database.insert(email_management_table, columns=email_management_table_columns,
                                values=(mail_id, From, ReceivedTime))
                continue

            elif subject is None or "断电账号" not in subject:
                logging.info(f'subject is none or not meet the requirements :{mail_id}')
                database.insert(email_management_table, columns=email_management_table_columns,
                                values=(mail_id, From, ReceivedTime))
                continue

            else:
                header_list.append([mail_id, From, ReceivedTime])
        except Exception as e:
            logging.error(f"{e}", exc_info=True)
    return header_list


async def select_email(imap, sender_email):
    # 选择收件箱
    status, messages = await imap.select("INBOX")

    if status != 'OK':
        logging.error("Failed to select mailbox.")
        raise Exception(f"Error selecting INBOX: {messages}")

    # 获取前30天的日期
    date_start = (datetime.now() - timedelta(days=30)).strftime("%d-%b-%Y")

    # 构造搜索条件：发件人 + 前30天日期
    search_criteria = f'(FROM "{sender_email}" SINCE "{date_start}")'

    # 搜索符合条件的邮件
    status, data = await imap.search(search_criteria)
    if status == 'OK':
        return data
    else:
        logging.error(f"select email failed {status}")
        raise Exception(f"select email failed {status}")


def remove_processed_items(mail_ids, database, email_management_table, email_management_table_columns):
    not_added_mail_ids = list()
    for mail_id in mail_ids:
        if database.isNotRepetitive(email_management_table, email_management_table_columns[0], mail_id):
            not_added_mail_ids.append(mail_id)
    return not_added_mail_ids


def email_processing(msg_data, database, power_outage_account_table, power_outage_account_table_columns, email_management_table, email_management_table_columns):
    if msg_data[0] == 'OK':
        # 解析消息
        msg = email.message_from_bytes(msg_data[2][1])
        # 解码主题
        subject = msg.get("subject", None)
        # 解码发件人
        From = msg.get("from", None)
        # 解码接受时间
        ReceivedTime = convert_email_time_format(msg.get("Date", None))

        try:
            subject = fileNameBase64Decode(subject)
        except Exception as e:
            logging.error(f"{e}", exc_info=True)

        if ReceivedTime is None:
            logging.warning("No ReceivedTime found in message")
            database.insert(email_management_table, columns=email_management_table_columns, values=(msg_data[1], From, ReceivedTime))
            return None

        if isinstance(subject, bytes):
            subject = subject.decode()

        # 打印主题
        logging.info(f"Subject: {subject}")

        # 打印发件人
        logging.info(f'From: {From}')

        # 打印接收时间
        logging.info(f'Received Time: {msg.get("Date")}')

        process_part(msg, database, power_outage_account_table, power_outage_account_table_columns,
                     base_path="./attachments")

        if database.isNotRepetitive(email_management_table, email_management_table_columns[0], msg_data[1]):
            database.insert(email_management_table, email_management_table_columns, (msg_data[1], From, ReceivedTime))


async def start_detection(email_address, password, ctx, host, port, sender_email, database_user, database_password,
                        database_host, database_port, database_server_name, power_outage_account_table,
                        power_outage_account_table_columns, email_management_table, email_management_table_columns, event=None):

    dsn_tns = cx_Oracle.makedsn(database_host, database_port, service_name=database_server_name)
    # 加载数据库
    logging.info("Connecting to database...")
    database = OracleDatabase(database_user, database_password, dsn_tns)
    logging.info("Database connection successful")

    try:
        # 连接邮件服务器
        logging.info("connecting to email server...")
        imap = aioimaplib.IMAP4_SSL(host=host, port=port, ssl_context=ctx, timeout=10)

        await imap.wait_hello_from_server()
        await imap.login(user=email_address, password=password)

        logging.info("Email server connected successfully.")

    except Exception as e:
        logging.error(f'imap connection failed:{e}')
        return None

    try:
        # 搜索符合条件的邮件
        data = await select_email(imap, sender_email)
        mail_ids = data[0].split()
        mail_ids = [str(int(mail_id)) for mail_id in mail_ids]

        # 移除已经处理过的邮件
        mail_ids = remove_processed_items(mail_ids, database, email_management_table, email_management_table_columns)

        # 通过标题筛选
        mail_ids = await header_selection(imap, mail_ids, database, email_management_table,
                                          email_management_table_columns)

        # 只处理最后一个
        if len(mail_ids) == 0:
            logging.info("No new emails")
            return False
        else:
            for mail_id in mail_ids[:-1]:
                database.insert(email_management_table, email_management_table_columns, (mail_id[0], mail_id[1], mail_id[2]))
            mail_ids = [mail_ids[-1][0]]

        logging.info(f"Email (ID): {mail_ids}")

        logging.info("Requesting email...")
        # 请求邮件
        msg_data_list = list()
        for mail_id in mail_ids:
            res, msg_data = await imap.fetch(mail_id, "(RFC822)")
            msg_data_list.append([res, mail_id, msg_data])
        logging.info("Email request successful")

        # 解析邮件
        for msg_data in msg_data_list:
            email_processing(msg_data, database, power_outage_account_table, power_outage_account_table_columns, email_management_table, email_management_table_columns)
    except Exception as e:
        logging.error(f"{e}", exc_info=True)
    finally:
        await imap.logout()
        database.close()
        if event is not None:
            event.set()


if __name__ == "__main__":
    # 账户凭据
    email_address = "example@example.com"
    password = "123456"

    # 设置加密套件
    ctx = ssl.create_default_context()
    ctx.set_ciphers('DEFAULT')

    # IMAP服务器信息
    host = "imap.example.com"
    port = 993

    # 发件人条件
    sender_email = 'example@example.com'

    # 数据库
    database_user = 'scott'
    database_password = '123456'
    database_host = 'localhost'
    database_port = 1521
    database_server_name = 'orcl'

    power_outage_account_table = 'POWEROUTAGEACCOUNT'
    power_outage_account_table_columns = ("TIME", "ACCOUNT")

    email_management_table = 'EMAIL'
    email_management_table_columns = ("EMAILID", "FROMEMAIL", "RECEIVEDTIME")

    asyncio.run(start_detection(email_address, password, ctx, host, port, sender_email, database_user, database_password,
                                database_host, database_port, database_server_name, power_outage_account_table,
                                power_outage_account_table_columns, email_management_table,
                                email_management_table_columns))
