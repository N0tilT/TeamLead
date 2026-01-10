from database import DatabaseConfig, DatabaseConnection
import psycopg2
from psycopg2 import sql


class MigrationManager:
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.connection = DatabaseConnection(self.config)

    def setup_database(self):
        """Create database if it doesn't exist"""
        print("Setting up database...")
        return DatabaseConnection.create_database(self.config)

    def create_tables(self):
        """Create tables in the database"""
        print("Creating tables...")
        
        conn = None
        cursor = None
        
        try:
            conn = self.connection.get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                CREATE TABLE analysis_results (
                id SERIAL PRIMARY KEY,
                tracking_id VARCHAR(256) NOT NULL,
                change_summary TEXT NOT NULL,
                tasks JSONB NOT NULL,
                risks JSONB DEFAULT '[]',
                keywords JSONB DEFAULT '{}',
                overall_description TEXT DEFAULT '',
                metrics JSONB DEFAULT '{"changes_processed":0, "tasks_generated":0, "risks_identified":0, "avg_task_priority":"", "trends":""}',
                tracker_ids JSONB DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            ''')
            cursor.execute('''
                CREATE INDEX idx_tracking_id ON analysis_results(tracking_id);
            ''')
            
            conn.commit()
            print("Tables created successfully.")
            
        except psycopg2.Error as e:
            print(f"Error creating tables: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def drop_database(self):
        """Drop database - use with caution!"""
        conn = None
        try:
            server_params = self.config.get_server_params()
            server_params['database'] = 'postgres'
            conn = psycopg2.connect(**server_params)
            conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            
            cursor.execute(sql.SQL("""
                SELECT pg_terminate_backend(pg_stat_activity.pid)
                FROM pg_stat_activity
                WHERE pg_stat_activity.datname = %s
                AND pid <> pg_backend_pid()
            """), [self.config.database])
            
            cursor.execute(
                sql.SQL("DROP DATABASE IF EXISTS {}").format(
                    sql.Identifier(self.config.database)
                )
            )
            print(f"Database '{self.config.database}' dropped successfully.")
            cursor.close()
            
        except psycopg2.Error as e:
            print(f"Error dropping database: {e}")
            return False
        finally:
            if conn:
                conn.close()
        return True

    def setup(self):
        """Complete setup: create database and tables"""
        print("Starting setup...")
        
        if not self.setup_database():
            print("Failed to create database. Exiting...")
            return False
        
        try:
            self.create_tables()
            print("Setup completed successfully!")
            return True
        except Exception as e:
            print(f"Setup failed: {e}")
            return False

    def reset(self):
        """Reset database: drop and recreate (for testing/development)"""
        print("Resetting database...")
        self.drop_database()
        return self.setup()