import cx_Oracle
import logging

logging.basicConfig(
    level=logging.INFO,
    handlers=[logging.StreamHandler()]  # 输出到控制台
)


class OracleDatabase:
    def __init__(self, user, password, dsn):
        self.user = user
        self.password = password
        self.dsn = dsn
        self.connection = cx_Oracle.connect(self.user, self.password, self.dsn)
        self.cursor = self.connection.cursor()

    def close(self):
        if self.connection:
            self.cursor.close()
            self.connection.close()
            logging.info("Oracle connection is closed")

    def isNotRepetitive(self, table_name, column, value):
        query = f"SELECT * FROM {table_name} WHERE {column} LIKE {value}"
        # print(query)
        try:
            self.cursor.execute(query)
            result = self.cursor.fetchall()
            if len(result) == 0:
                return True
            else:
                return False

        except Exception as e:
            logging.error(e)

    def insert(self, table_name, columns, values):
        if type(columns) is not tuple:
            columns = tuple(columns)
        if type(values) is not tuple:
            values = tuple(values)

        columns_str = ', '.join(columns)
        placeholders = [f" :{i}" for i in range(1, len(values)+1)]
        placeholders = ', '.join(placeholders)

        query = f"INSERT INTO {table_name}({columns_str}) VALUES ({placeholders})"
        logging.info(f"Executing query: {query} with values: {values}")
        try:
            self.cursor.execute(query, values)
            self.connection.commit()
        except Exception as e:
            logging.error(e, exc_info=True)
            self.connection.rollback()

    def insert_many(self, table_name, columns: tuple, values: list):
        columns_str = ', '.join(columns)

        placeholders = [f" :{i}" for i in range(1, len(columns) + 1)]
        placeholders = ', '.join(placeholders)

        query = f"INSERT INTO {table_name}({columns_str}) VALUES ({placeholders})"
        try:
            self.cursor.executemany(query, values)
            self.connection.commit()
            logging.info("Batch insert data")
            return True
        except Exception as e:
            logging.error(e, exc_info=True)
            self.connection.rollback()
            return False

    def clear_table(self, table_name):
        query = f"SELECT COUNT(*) FROM {table_name}"
        count = self.cursor.execute(query).fetchone()[0]
        if count == 0:
            return None

        query = f"DELETE FROM {table_name}"
        try:
            self.cursor.execute(query)
            self.connection.commit()
            logging.info("Batch delete data")
        except Exception as e:
            logging.error(e)

            self.connection.rollback()


if __name__ == '__main__':
    data = OracleDatabase('scott', 'Aa123456', 'orcl')

    data.clear_table('EMAIL')
