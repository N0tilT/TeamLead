# database.py
import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

class DatabaseConfig:
    '''Класс конфигурации БД'''
    def __init__(self,
                 database: str = "", 
                 host: str = "", 
                 user: str = "", 
                 password: str = "",
                 port: int = 5432):
        self.host = host
        self.database = database
        self.user = user
        self.password = password
        self.port = port

    def get_connection_params(self):
        return {
            'host': self.host,
            'database': self.database,
            'user': self.user,
            'password': self.password,
            'port': self.port
        }
    
    def get_server_params(self):
        """Get connection params for connecting to PostgreSQL server (without database)"""
        return {
            'host': self.host,
            'user': self.user,
            'password': self.password,
            'port': self.port
        }


class DatabaseConnection:
    '''Класс подключения к БД'''
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self._connection = None
    
    def get_connection(self):
        if self._connection is None or self._connection.closed:
            self._connection = psycopg2.connect(**self.config.get_connection_params())
        return self._connection

    def close_connection(self):
        if self._connection and not self._connection.closed:
            self._connection.close()

    @staticmethod
    def create_database(config: DatabaseConfig):
        """
        Create a new database on PostgreSQL server
        Connects to default 'postgres' database first, then creates target database
        """
        server_params = config.get_server_params()
        server_params['database'] = 'postgres'
        
        conn = None
        try:
            conn = psycopg2.connect(**server_params)
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            
            cursor.execute(
                sql.SQL("SELECT 1 FROM pg_database WHERE datname = %s"),
                [config.database]
            )
            
            exists = cursor.fetchone()
            
            if not exists:
                cursor.execute(
                    sql.SQL("CREATE DATABASE {}").format(
                        sql.Identifier(config.database)
                    )
                )
                print(f"Database '{config.database}' created successfully.")
            else:
                print(f"Database '{config.database}' already exists.")
            
            cursor.close()
            return True
            
        except psycopg2.Error as e:
            print(f"Error creating database: {e}")
            return False
        finally:
            if conn:
                conn.close()