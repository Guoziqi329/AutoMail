import shutil
import ssl
import time
import tkinter
from pathlib import Path
import threading
import customtkinter as ctk
from AutoEmail import start_detection
from tkinter import messagebox, StringVar, filedialog, scrolledtext
import json
import os
import logging
from logging import Filter
import asyncio

logging.basicConfig(
    level=logging.INFO,
    handlers=[logging.StreamHandler()]  # 输出到控制台
)


# 自定义日志过滤器
class LevelFilter(Filter):
    def __init__(self, level):
        self.level = level

    def filter(self, record):
        return record.levelno == self.level


# 自定义日志处理器（用于 GUI 显示）
class TextHandler(logging.Handler):
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record):
        msg = self.format(record) + "\n"

        def append_log():
            self.text_widget.configure(state='normal')
            self.text_widget.insert(tkinter.END, msg)
            self.text_widget.configure(state='disabled')
            self.text_widget.see(tkinter.END)
        self.text_widget.after(0, append_log)


class data_management():
    def __init__(self):
        self.data_path = "./data"

        # 判断是否有data文件夹
        if not os.path.exists(self.data_path) or not os.path.exists(os.path.join(self.data_path, 'set.json')):
            # 没有就创建data和logging
            self.log_path = "./data/logging"
            self.creat_dir(self.log_path)
            self.update_set_data({"log_path": self.log_path})
        else:
            with open(os.path.join(self.data_path, 'set.json'), 'r') as f:
                self.json_data = dict(json.load(f))
                if "log_path" in self.json_data.keys():
                    self.log_path = self.json_data["log_path"]
                    self.creat_dir(self.log_path)
                else:
                    self.log_path = "./data/logging"
                    self.json_data["log_path"] = "./data/logging"
                    self.update_set_data(self.json_data)
        print(self.data_path)
        print(self.log_path)

        Path(os.path.join(self.log_path, "error.log")).touch(exist_ok=True)
        Path(os.path.join(self.log_path, "warning.log")).touch(exist_ok=True)
        Path(os.path.join(self.log_path, "info.log")).touch(exist_ok=True)

        with open(os.path.join(self.data_path, 'set.json'), 'r') as f:
            self.json_data = dict(json.load(f))
            intact_list = ["log_path", "email_address", "email_password", "email_host", "email_port", "sender_email", "database_user",
                           "database_password", "database_host", "database_port", "database_server_name", "power_off_table_name",
                           "power_off_time_column", "power_off_account_column", "email_management_table_name", "email_management_email_id_column",
                           "email_management_receive_from_column", "email_management_receive_time_column", "loop", "interval_time"]
            intact_list = [item for item in intact_list if item not in self.json_data.keys()]

            if len(intact_list) != 0:
                for item in intact_list:
                    self.json_data[item] = None
                self.update_set_data(self.json_data)

        with open(os.path.join(self.data_path, 'set.json'), 'r') as f:
            self.set_data = dict(json.load(f))

    def get_set_data(self):
        return self.set_data

    def update_set_data(self, set_data):
        self.set_data = set_data
        with open(os.path.join(self.data_path, 'set.json'), 'w') as f:
            json.dump(self.set_data, f)

    def creat_dir(self, path):
        if not os.path.exists(path):
            os.makedirs(path)

    def update_logging_dir(self, target_folders):
        # 检查目录是否存在
        if not os.path.exists(self.set_data["log_path"]):
            print(f"目录 {self.set_data['log_path']} 不存在")
        if target_folders == self.json_data["log_path"]:
            return None
        self.creat_dir(target_folders)
        for file_name in os.listdir(self.set_data["log_path"]):
            source_file = os.path.join(self.set_data["log_path"], file_name)
            target_file = os.path.join(target_folders, file_name)
            if os.path.isdir(source_file):
                shutil.copytree(source_file, target_file)
            else:
                shutil.copy(source_file, target_file)

        # 遍历目录中的所有文件和子目录
        for filename in os.listdir(self.set_data["log_path"]):
            file_path = os.path.join(self.set_data["log_path"], filename)

            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)  # 删除文件或符号链接
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)  # 删除子目录及其内容

        self.set_data["log_path"] = target_folders
        self.update_set_data(self.set_data)


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.data_management = data_management()
        self.set_data = self.data_management.get_set_data()

        # 设置窗口标题和大小
        self.title("Auto Email")
        self.geometry("1000x550")

        # 设置网格布局
        self.grid_columnconfigure(1, weight=1)  # 主内容区域可伸缩
        self.grid_rowconfigure(0, weight=1)

        # 创建侧边栏
        self.sidebar_frame = ctk.CTkFrame(self, width=180, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(6, weight=1)

        # 侧边栏标题
        ctk.CTkLabel(self.sidebar_frame, text="Auto Email", height=95, font=ctk.CTkFont(size=20, weight="bold")).grid(row=0, column=0, padx=20, pady=(20, 10))

        # 侧边栏按钮
        ctk.CTkButton(self.sidebar_frame, text="Home", command=self.show_home, width=150).grid(row=1, column=0, padx=25, pady=10)
        ctk.CTkButton(self.sidebar_frame, text="Email Server", command=self.show_page1, width=150).grid(row=2, column=0, padx=25, pady=10)
        ctk.CTkButton(self.sidebar_frame, text="Database Server", command=self.show_page2, width=150).grid(row=3, column=0, padx=25, pady=10)
        ctk.CTkButton(self.sidebar_frame, text="Database Field Settings", command=self.show_page3, width=150).grid(row=4, column=0, padx=25, pady=10)
        ctk.CTkButton(self.sidebar_frame, text="Log Settings", command=self.show_page4, width=150).grid(row=5, column=0, padx=25, pady=10)

        # 主内容区域
        self.main_frame = ctk.CTkFrame(self, corner_radius=0)
        self.main_frame.grid(row=0, column=1, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)

        # 初始化日志系统
        self.setup_logging()

        # 当前显示的页面
        self.current_frame = None

        self.number_of_executions = 0

        # 默认显示主页
        self.show_home()

    def email_thread(self, email_address, password, ctx, email_host, email_port, sender_email, database_user,
                     database_password, database_host, database_port, database_server_name, power_off_table_name,
                     power_outage_account_table_columns, email_management_table_name, email_management_table_columns):
        self.number_of_executions = self.number_of_executions + 1
        check_number = self.number_of_executions
        if self.set_data["loop"] is True:
            while self.set_data["loop"] and check_number == self.number_of_executions:
                self.show_logging()
                time.sleep(1)
                # 初始化日志系统
                self.setup_logging()
                time.sleep(0.2)
                logging.info("Start loop")
                asyncio.run(
                    start_detection(email_address, password, ctx, email_host, email_port, sender_email, database_user,
                                    database_password, database_host, database_port, database_server_name,
                                    power_off_table_name, power_outage_account_table_columns,
                                    email_management_table_name, email_management_table_columns))
                self.show_home()
                time.sleep(int(self.set_data["interval_time"])*60)
        else:
            asyncio.run(
                start_detection(email_address, password, ctx, email_host, email_port, sender_email, database_user,
                                database_password, database_host, database_port, database_server_name,
                                power_off_table_name, power_outage_account_table_columns,
                                email_management_table_name, email_management_table_columns))
            self.show_home()

    def clear_main_frame(self):
        """清除主内容区域的当前内容"""
        if self.current_frame is not None:
            self.current_frame.destroy()
        self.current_frame = None

    def toggle_textbox_state(self):
        """根据复选框的状态切换文本框是否可用"""
        if self.checkbox_var.get():
            self.textbox.configure(state='normal')
            self.set_data["loop"] = True
            self.set_data["interval_time"] = self.textbox.get()
            self.data_management.update_set_data(self.set_data)
        else:
            self.textbox.configure(state='disabled')
            self.set_data["loop"] = False
            self.set_data["interval_time"] = self.textbox.get()
            self.data_management.update_set_data(self.set_data)

    def show_logging(self):
        self.clear_main_frame()
        self.current_frame = ctk.CTkFrame(self.main_frame)
        self.current_frame.grid(row=0, column=0, columnspan=2, sticky="nsew", padx=20, pady=20)

        # 添加日志显示区域
        self.log_area = scrolledtext.ScrolledText(self.current_frame, wrap=tkinter.WORD, state='disabled')
        self.log_area.pack(padx=10, pady=10, fill=tkinter.BOTH, expand=True)

    def email_detection(self):
        if None in self.set_data.values() or "" in self.set_data.values():
            # 初始化日志系统
            self.setup_logging()
            logging.warning("There are null values in the data, please enter complete information.")
            messagebox.showwarning("Warning", "There are null values in the data, please enter complete information.")
            return None

        self.show_logging()
        # 初始化日志系统
        self.setup_logging()

        logging.info("Start scanning emails")

        # 邮箱账户凭据
        email_address = self.set_data["email_address"]
        password = self.set_data["email_password"]

        # 设置加密套件
        ctx = ssl.create_default_context()
        ctx.set_ciphers("DEFAULT")

        # 设置IMAP服务器信息
        email_host = self.set_data["email_host"]
        email_port = int(self.set_data["email_port"])

        # 发件人条件
        sender_email = self.set_data["sender_email"]

        # 数据库信息
        database_user = self.set_data["database_user"]
        database_password = self.set_data["database_password"]
        database_host = self.set_data["database_host"]
        database_port = int(self.set_data["database_port"])
        database_server_name = self.set_data["database_server_name"]

        power_off_table_name = self.set_data["power_off_table_name"]
        power_outage_account_table_columns = (self.set_data["power_off_time_column"], self.set_data["power_off_account_column"])

        email_management_table_name = self.set_data["email_management_table_name"]
        email_management_table_columns = (self.set_data["email_management_email_id_column"], self.set_data["email_management_receive_from_column"], self.set_data["email_management_receive_time_column"])

        # print(email_address, password, email_host, email_port, sender_email, database_user, database_password, database_host, database_port, database_server_name, power_off_table_name, power_outage_account_table_columns, email_management_table_name, email_management_table_columns)

        thread = threading.Thread(target=self.email_thread, args=(email_address, password, ctx, email_host, email_port, sender_email, database_user, database_password, database_host, database_port, database_server_name, power_off_table_name, power_outage_account_table_columns, email_management_table_name, email_management_table_columns))
        thread.start()

    def setup_logging(self):
        # 清除旧的 Handler
        for handler in logging.getLogger().handlers[:]:
            logging.getLogger().removeHandler(handler)

        # 设置日志格式
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        # 获取根日志器
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)

        levels = {
            logging.ERROR: (self.set_data["log_path"] + "/error.log", "ERROR"),
            logging.WARNING: (self.set_data["log_path"] + "/warning.log", "WARNING"),
            logging.INFO: (self.set_data["log_path"] + "/info.log", "INFO")
        }
        for level, (filename, level_name) in levels.items():
            handler = logging.FileHandler(filename, encoding='utf-8')
            handler.setLevel(level)
            handler.setFormatter(formatter)
            handler.addFilter(LevelFilter(level))
            logger.addHandler(handler)

        try:
            text_handler = TextHandler(self.log_area)
            text_handler.setLevel(logging.INFO)
            text_handler.setFormatter(formatter)
            logger.addHandler(text_handler)
        except NameError:
            pass
        except Exception as e:
            logging.error(e)

        logger.addHandler(logging.StreamHandler())

    def show_home(self):
        """显示主页"""
        if self.set_data["loop"] is None or self.set_data["interval_time"] is None:
            self.set_data["loop"] = True
            self.set_data["interval_time"] = 60
            self.data_management.update_set_data(self.set_data)

        self.clear_main_frame()
        self.current_frame = ctk.CTkFrame(self.main_frame)
        self.current_frame.grid(row=0, column=0, columnspan=2, sticky="nsew", padx=20, pady=20)

        ctk.CTkLabel(self.current_frame, text="Welcome to the automatic email.", font=ctk.CTkFont(size=25, weight="bold")).grid(row=0, column=0, columnspan=5, padx=40, pady=30)

        # 添加按钮
        ctk.CTkButton(self.current_frame, text="start", font=ctk.CTkFont(size=15), command=self.email_detection).grid(row=1, column=0, columnspan=3, padx=50, pady=50)

        # 创建一个框架来包含复选框和文本框
        checkbox_textbox_frame = ctk.CTkFrame(self.current_frame)
        checkbox_textbox_frame.grid(row=1, column=4, columnspan=4, rowspan=2, padx=30, pady=50)

        # 添加复选框
        self.checkbox_var = ctk.BooleanVar(value=self.set_data["loop"])
        ctk.CTkCheckBox(checkbox_textbox_frame, text="Enable loop wait", font=ctk.CTkFont(size=15), variable=self.checkbox_var, command=self.toggle_textbox_state).grid(row=0, column=0, columnspan=3, padx=30, pady=(15, 5))

        # 添加“each”标签
        ctk.CTkLabel(checkbox_textbox_frame, text="each", font=ctk.CTkFont(size=15)).grid(row=1, column=0, padx=(20, 5), pady=(10, 15))

        # 添加文本框
        self.textbox = ctk.CTkEntry(checkbox_textbox_frame, placeholder_text="Please input time", state="normal" if self.set_data["loop"] is True else "disabled", width=40, height=20, textvariable=ctk.StringVar(value=self.set_data["interval_time"]))
        self.textbox.grid(row=1, column=1, padx=3, pady=(10, 15))

        # 添加“minutes”标签
        ctk.CTkLabel(checkbox_textbox_frame, text="minutes", font=ctk.CTkFont(size=15)).grid(row=1, column=2, padx=(5, 20), pady=(10, 15))

    def page1_and_page2_frame(self, row, column, text, placeholder_text, key_name):
        default = self.set_data[key_name]
        if default is not None:
            default = StringVar(value=default)
        # 创建一个框架来包含标签和文本框
        labeled_textbox_frame = ctk.CTkFrame(self.current_frame)
        labeled_textbox_frame.grid(row=row, column=column, columnspan=6, padx=35, pady=3, sticky="ew")

        label = ctk.CTkLabel(labeled_textbox_frame, text=text, font=ctk.CTkFont(size=15), width=175)
        label.pack(side="left", padx=0, pady=0)

        # 添加文本框
        entry = ctk.CTkEntry(labeled_textbox_frame, placeholder_text=placeholder_text, width=250, textvariable=default)
        entry.pack(padx=50, pady=10)
        self.updateData.append([key_name, entry])

    def get_email_data(self):
        for entry in self.updateData:
            self.set_data[entry[0]] = entry[1].get()
        self.data_management.update_set_data(self.set_data)
        messagebox.showinfo("info", "Email settings information updated.")

    def show_page1(self):
        """Email Settings Page"""

        self.clear_main_frame()
        self.current_frame = ctk.CTkFrame(self.main_frame)
        self.current_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)

        welcome_label = ctk.CTkLabel(self.current_frame, text="Email settings",
                                     font=ctk.CTkFont(size=25, weight="bold"))
        welcome_label.grid(row=0, column=0, columnspan=5, padx=40, pady=30, sticky="w")

        # 创建文本框
        self.updateData = list()
        self.page1_and_page2_frame(1, 0, "email address", "Please enter your email address", "email_address")
        self.page1_and_page2_frame(2, 0, "email password", "Please enter your email password", "email_password")
        self.page1_and_page2_frame(3, 0, "email host", "Please enter your email host", "email_host")
        self.page1_and_page2_frame(4, 0, "email port", "Please enter your email post", "email_port")
        self.page1_and_page2_frame(5, 0, "sender condition", "Please enter sender condition", "sender_email")

        # 添加按钮
        button = ctk.CTkButton(self.current_frame, text="update", command=self.get_email_data)
        button.grid(row=6, column=0, columnspan=6, padx=20, pady=25)

    def get_database_data(self):
        for entry in self.updateData:
            self.set_data[entry[0]] = entry[1].get()
        self.data_management.update_set_data(self.set_data)
        messagebox.showinfo("info", "Database information updated.")

    def show_page2(self):
        """Database Settings Page"""
        self.clear_main_frame()
        self.current_frame = ctk.CTkFrame(self.main_frame)
        self.current_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)

        welcome_label = ctk.CTkLabel(self.current_frame, text="Database server",
                                     font=ctk.CTkFont(size=25, weight="bold"))
        welcome_label.grid(row=0, column=0, columnspan=5, padx=40, pady=30, sticky="w")

        self.updateData = list()
        self.page1_and_page2_frame(1, 0, "Database user", "Please enter your database user", "database_user")
        self.page1_and_page2_frame(2, 0, "Database password", "Please enter your database password", 'database_password')
        self.page1_and_page2_frame(3, 0, "Database host", "Please enter your database host", 'database_host')
        self.page1_and_page2_frame(4, 0, "Database post", "Please enter your database post", "database_port")
        self.page1_and_page2_frame(5, 0, "Database server name", "Please enter your database server name", "database_server_name")

        # 添加按钮
        update_button = ctk.CTkButton(self.current_frame, text="update", command=self.get_database_data)
        update_button.grid(row=6, column=0, columnspan=6, padx=20, pady=25)

    def page3_label_and_entry(self, format, row, text, placeholder_text, key_name):
        default = self.set_data[key_name]
        if default is not None:
            default = StringVar(value=default)

        ctk.CTkLabel(format, text=text, font=ctk.CTkFont(size=15), width=200).grid(row=row, column=0, padx=0, pady=5, sticky="nsew")
        entry_table1_name = ctk.CTkEntry(format, placeholder_text=placeholder_text, width=350, textvariable=default)
        entry_table1_name.grid(row=row, column=1, padx=30, pady=5, sticky="nsew")
        self.database_column_data.append([key_name, entry_table1_name])

    def update_database_fields(self):
        for entry in self.database_column_data:
            self.set_data[entry[0]] = entry[1].get()
        self.data_management.update_set_data(self.set_data)
        messagebox.showinfo("info", "Database information updated.")

    def show_page3(self):
        """Database Settings Page"""
        self.clear_main_frame()
        self.current_frame = ctk.CTkFrame(self.main_frame)
        self.current_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)

        ctk.CTkLabel(self.current_frame, text="Database Field Settings", font=ctk.CTkFont(size=25, weight="bold")).grid(row=0, column=0, columnspan=5, padx=40, pady=30, sticky="w")

        self.database_column_data = list()

        # 创建断电账号框架
        frame_of_power_outage_account = ctk.CTkFrame(self.current_frame)
        frame_of_power_outage_account.grid(row=1, column=0, columnspan=6, padx=35, pady=3, sticky="ew")

        # 添加断电账号表标签
        ctk.CTkLabel(frame_of_power_outage_account, text="Database of power-off account", font=ctk.CTkFont(size=17), height=30, width=250).grid(row=0, column=0, columnspan=4, padx=150, pady=3)

        # 添加断电账号表名标签和文本框
        self.page3_label_and_entry(frame_of_power_outage_account, 1, "Table name", "Please enter the name of the power-off account table", "power_off_table_name")

        # 添加时间字段标签和文本框
        self.page3_label_and_entry(frame_of_power_outage_account, 2, "Time column", "Please enter the name of the time column", "power_off_time_column")

        # 添加账号字段标签和文本框
        self.page3_label_and_entry(frame_of_power_outage_account, 3, "Account column", "Please enter the name of the account column", "power_off_account_column")

        # 创建邮件管理框架
        frame_of_email_management = ctk.CTkFrame(self.current_frame)
        frame_of_email_management.grid(row=2, column=0, columnspan=6, padx=35, pady=3, sticky="ew")

        # 添加邮件管理表标签
        ctk.CTkLabel(frame_of_email_management, text="Database of email management table", font=ctk.CTkFont(size=17), height=30, width=250).grid(row=0, column=0, columnspan=4, padx=150, pady=3)

        # 添加邮件管理表的标签和文本框
        self.page3_label_and_entry(frame_of_email_management, 1, "Table name", "Please enter the name of the email management table", "email_management_table_name")

        # 添加emailId字段的标签和文本框
        self.page3_label_and_entry(frame_of_email_management, 2, "Email ID column", "Please enter the name of the email ID column", "email_management_email_id_column")

        # 添加received from字段的标签和文本框
        self.page3_label_and_entry(frame_of_email_management, 3, "Received from column", "Please enter the name of the received from column", "email_management_receive_from_column")

        # 添加received time字段的标签和文本框
        self.page3_label_and_entry(frame_of_email_management, 4, "Received time column", "Please enter the name of the received time column", "email_management_receive_time_column")

        update_button = ctk.CTkButton(self.current_frame, text="update", command=self.update_database_fields)
        update_button.grid(row=3, column=0, columnspan=6, padx=20, pady=25)

    def select_file(self):
        """打开文件选择对话框并更新文本框中的文件路径"""
        self.directory_path = filedialog.askdirectory(title="选择文件夹")
        if self.directory_path:
            self.file_path_var.set(self.directory_path)

    def folder_update(self):
        self.data_management.update_logging_dir(self.file_entry.get())
        for item in self.logging_info_list:
            item[1].configure(state="normal")
            item[1].delete(0, "end")
            route = self.set_data["log_path"] + '/' + item[0] + ".log"
            item[1].insert("end", route)
            item[1].configure(state="disabled")

    def show_logging_dir_info(self, info_frame, row, text, default, level):
        if default is not None:
            default = StringVar(value=default + '/' + level + '.log')

        label = ctk.CTkLabel(info_frame, text=text, font=ctk.CTkFont(size=15), width=100)
        label.grid(row=row, column=0, padx=40, pady=10)

        # 添加文本框
        entry = ctk.CTkEntry(info_frame, placeholder_text=None, width=350, textvariable=default, state="disabled")
        entry.grid(row=row, column=1, padx=40, pady=10)
        self.logging_info_list.append([level, entry])

    def show_page4(self):
        """Log Settings Page"""
        self.clear_main_frame()
        self.current_frame = ctk.CTkFrame(self.main_frame)
        self.current_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)

        welcome_label = ctk.CTkLabel(self.current_frame, text="Log settings",
                                     font=ctk.CTkFont(size=25, weight="bold"))
        welcome_label.grid(row=0, column=0, columnspan=5, padx=40, pady=30, sticky="w")

        # 创建一个框架来包含标签、文本框和按钮
        file_selection_frame = ctk.CTkFrame(self.current_frame)
        file_selection_frame.grid(row=1, column=0, columnspan=6, padx=35, pady=10, sticky="ew")

        # 添加标签
        label = ctk.CTkLabel(file_selection_frame, text="Select folder:", font=ctk.CTkFont(size=16), width=130)
        label.pack(side="left", padx=(10, 5), pady=10)

        # 添加文本框来显示文件路径
        self.file_path_var = StringVar(value=self.set_data["log_path"])
        self.file_entry = ctk.CTkEntry(file_selection_frame, textvariable=self.file_path_var, placeholder_text="Select folder path",
                                       width=300)
        self.file_entry.pack(side="left", padx=5, pady=10)

        # 添加按钮来选择文件
        self.select_folder_button = ctk.CTkButton(file_selection_frame, text="Select folder", command=self.select_file)
        self.select_folder_button.pack(side="left", padx=10, pady=10)

        logging_information_frame = ctk.CTkFrame(self.current_frame)
        logging_information_frame.grid(row=2, column=0, columnspan=6, padx=35, pady=10)
        self.logging_info_list = list()
        self.show_logging_dir_info(logging_information_frame, 0,  "Error logging file", self.set_data["log_path"], "error")
        self.show_logging_dir_info(logging_information_frame, 1,  "Warning logging file", self.set_data["log_path"], "warning")
        self.show_logging_dir_info(logging_information_frame, 2,  "Info logging file", self.set_data["log_path"], "info")

        update_button = ctk.CTkButton(self.current_frame, text="update", command=self.folder_update)
        update_button.grid(row=6, column=0, columnspan=6, padx=20, pady=25)


if __name__ == "__main__":
    ctk.set_appearance_mode("Light")  # 设置外观模式：Light, Dark, System
    ctk.set_default_color_theme("blue")  # 设置主题颜色
    app = App()
    app.mainloop()
