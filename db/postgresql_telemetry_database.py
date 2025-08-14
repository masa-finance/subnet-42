import psycopg2
import psycopg2.extras
from threading import Lock
import os
from fiber.logging_utils import get_logger

logger = get_logger(__name__)


class PostgreSQLTelemetryDatabase:
    def __init__(self, host=None, port=None, database=None, user=None, password=None):
        """
        Initialize PostgreSQL telemetry database connection.

        Args:
            host: PostgreSQL host (default from env POSTGRES_HOST)
            port: PostgreSQL port (default from env POSTGRES_PORT)
            database: Database name (default from env POSTGRES_DB)
            user: Database user (default from env POSTGRES_USER)
            password: Database password (default from env
                POSTGRES_PASSWORD)
        """
        self.host = host or os.getenv("POSTGRES_HOST")
        self.port = port or os.getenv("POSTGRES_PORT", "5432")
        self.database = database or os.getenv("POSTGRES_DB", "telemetry")
        self.user = user or os.getenv("POSTGRES_USER", "telemetry_user")
        self.password = password or os.getenv("POSTGRES_PASSWORD", "telemetry_password")

        # Ensure host is provided
        if not self.host:
            raise ValueError(
                "PostgreSQL host must be provided via POSTGRES_HOST environment variable or host parameter"
            )

        self.lock = Lock()
        self.connection_pool = None

        # Test connection and create table if needed
        self._test_connection()
        logger.info(
            f"PostgreSQL telemetry database initialized: "
            f"{self.host}:{self.port}/{self.database}"
        )

    def _get_connection(self):
        """Get a database connection."""
        try:
            conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                cursor_factory=psycopg2.extras.RealDictCursor,
            )
            return conn
        except psycopg2.OperationalError as e:
            error_msg = str(e)
            if "database" in error_msg and "does not exist" in error_msg:
                logger.warning(
                    f"Database '{self.database}' does not exist, attempting to create it..."
                )
                try:
                    self._create_database()
                    # Try connecting again after creating the database
                    conn = psycopg2.connect(
                        host=self.host,
                        port=self.port,
                        database=self.database,
                        user=self.user,
                        password=self.password,
                        cursor_factory=psycopg2.extras.RealDictCursor,
                    )
                    logger.info(
                        f"Successfully created and connected to database '{self.database}'"
                    )
                    return conn
                except Exception as create_error:
                    logger.error(
                        f"Failed to create database '{self.database}': {create_error}"
                    )
                    logger.error("Please create the database manually using:")
                    logger.error(
                        f'  psql -h {self.host} -U postgres -c "CREATE DATABASE {self.database};"'
                    )
                    raise ConnectionError(
                        f"Database '{self.database}' does not exist and could not be created automatically."
                    )
            elif "password authentication failed" in error_msg:
                logger.error(f"PostgreSQL authentication failed for user '{self.user}'")
                logger.error(
                    "Please check your POSTGRES_USER and POSTGRES_PASSWORD environment variables"
                )
                raise ConnectionError(f"Authentication failed for user '{self.user}'")
            elif "connection to server" in error_msg and "failed" in error_msg:
                logger.error(
                    f"Cannot connect to PostgreSQL server at {self.host}:{self.port}"
                )
                logger.error("Please check if PostgreSQL is running and accessible")
                raise ConnectionError(
                    f"Cannot connect to PostgreSQL server at {self.host}:{self.port}"
                )
            else:
                logger.error(f"PostgreSQL connection error: {error_msg}")
                raise
        except psycopg2.Error as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise

    def _create_database(self):
        """Create the database by connecting to the default postgres database."""
        try:
            # First try with the configured user
            self._attempt_database_creation(self.user, self.password)
        except ConnectionError as e:
            if (
                "permission denied" in str(e).lower()
                or "must be owner" in str(e).lower()
            ):
                logger.warning(
                    f"User '{self.user}' lacks database creation permissions"
                )
                logger.info("Attempting to create database with postgres superuser...")
                try:
                    # Try with postgres superuser (common default)
                    postgres_password = os.getenv("POSTGRES_SUPERUSER_PASSWORD", "")
                    if postgres_password:
                        self._attempt_database_creation("postgres", postgres_password)
                        # Also create the user if it doesn't exist
                        self._ensure_user_exists("postgres", postgres_password)
                    else:
                        logger.warning(
                            "POSTGRES_SUPERUSER_PASSWORD not set, cannot use superuser fallback"
                        )
                        raise
                except Exception as superuser_error:
                    logger.error(
                        f"Failed to create database with superuser: {superuser_error}"
                    )
                    raise ConnectionError(f"Database creation failed: {e}")
            else:
                raise

    def _attempt_database_creation(self, username, password):
        """Attempt to create the database with given credentials."""
        try:
            # Connect to the default 'postgres' database to create our target database
            conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                database="postgres",  # Connect to default database
                user=username,
                password=password,
            )

            # Set autocommit to True for database creation
            conn.autocommit = True

            with conn.cursor() as cursor:
                # Check if database already exists
                cursor.execute(
                    "SELECT 1 FROM pg_database WHERE datname = %s", (self.database,)
                )

                if cursor.fetchone():
                    logger.info(f"Database '{self.database}' already exists")
                else:
                    # Create the database
                    cursor.execute(f"CREATE DATABASE {self.database}")
                    logger.info(
                        f"Created database '{self.database}' with user '{username}'"
                    )

            conn.close()

        except psycopg2.OperationalError as e:
            error_msg = str(e)
            if "password authentication failed" in error_msg:
                raise ConnectionError(
                    f"Authentication failed for user '{username}' when trying to create database"
                )
            else:
                raise ConnectionError(
                    f"Failed to connect to postgres database for database creation: {error_msg}"
                )
        except psycopg2.Error as e:
            raise ConnectionError(f"Database creation failed: {e}")

    def _ensure_user_exists(self, superuser, superuser_password):
        """Ensure the telemetry user exists and has proper permissions."""
        try:
            conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                database="postgres",
                user=superuser,
                password=superuser_password,
            )

            conn.autocommit = True

            with conn.cursor() as cursor:
                # Check if user exists
                cursor.execute("SELECT 1 FROM pg_user WHERE usename = %s", (self.user,))

                if not cursor.fetchone():
                    # Create the user
                    cursor.execute(
                        f"CREATE USER {self.user} WITH ENCRYPTED PASSWORD %s",
                        (self.password,),
                    )
                    logger.info(f"Created user '{self.user}'")

                # Grant privileges on the database
                cursor.execute(
                    f"GRANT ALL PRIVILEGES ON DATABASE {self.database} TO {self.user}"
                )
                logger.info(
                    f"Granted privileges on database '{self.database}' to user '{self.user}'"
                )

            conn.close()

        except Exception as e:
            logger.warning(f"Failed to ensure user exists: {e}")
            # Don't raise here as the database creation might still work

    def _test_connection(self):
        """Test the database connection."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    result = cursor.fetchone()
                    if result:
                        logger.info("PostgreSQL connection test successful")
                        # Test if telemetry table exists
                        self._ensure_table_exists(conn)
        except ConnectionError:
            # Re-raise connection errors with our custom messages
            raise
        except Exception as e:
            logger.error(f"PostgreSQL connection test failed: {e}")
            raise

    def _ensure_table_exists(self, conn):
        """Ensure the telemetry table exists and create it if it doesn't."""
        try:
            with conn.cursor() as cursor:
                # Check if table exists
                cursor.execute(
                    """
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'telemetry'
                    );
                """
                )
                table_exists = cursor.fetchone()["exists"]

                if not table_exists:
                    logger.warning("Telemetry table does not exist, creating it...")
                    self._create_table_and_indexes(cursor)
                    conn.commit()
                    logger.info("Telemetry table created successfully")
                else:
                    logger.debug("Telemetry table exists")
                    # Check for missing columns and add them
                    self._ensure_required_columns(cursor)
                    conn.commit()
        except Exception as e:
            logger.error(f"Failed to check/create telemetry table: {e}")
            raise

    def _create_table_and_indexes(self, cursor):
        """Create the telemetry table and indexes."""
        # Create the telemetry table with JSON stats storage
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS telemetry (
                id SERIAL PRIMARY KEY,
                hotkey VARCHAR(255) NOT NULL,
                uid VARCHAR(50),
                "timestamp" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                boot_time BIGINT,
                last_operation_time BIGINT,
                "current_time" BIGINT,
                worker_id VARCHAR(255),
                stats_json JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Create indexes
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_telemetry_hotkey ON telemetry(hotkey)",
            'CREATE INDEX IF NOT EXISTS idx_telemetry_timestamp ON telemetry("timestamp")',
            "CREATE INDEX IF NOT EXISTS idx_telemetry_created_at ON telemetry(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_telemetry_uid ON telemetry(uid)",
            "CREATE INDEX IF NOT EXISTS idx_telemetry_worker_id ON telemetry(worker_id)",
            "CREATE INDEX IF NOT EXISTS idx_telemetry_stats_json ON telemetry USING GIN (stats_json)",
            "CREATE INDEX IF NOT EXISTS idx_telemetry_hotkey_created_at ON telemetry(hotkey, created_at DESC)",
        ]

        for index_sql in indexes:
            cursor.execute(index_sql)

    def _ensure_required_columns(self, cursor):
        """Ensure all required columns exist in the telemetry table."""
        try:
            # Get current column names
            cursor.execute(
                """
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_schema = 'public' 
                AND table_name = 'telemetry'
                """
            )
            existing_columns = [row["column_name"] for row in cursor.fetchall()]

            # Define required columns that might be missing
            required_columns = [
                ("tiktok_transcription_success", "INTEGER DEFAULT 0"),
                ("tiktok_transcription_errors", "INTEGER DEFAULT 0"),
            ]

            # Add missing columns
            for column_name, column_definition in required_columns:
                if column_name not in existing_columns:
                    logger.info(f"Adding missing column: {column_name}")
                    cursor.execute(
                        f"ALTER TABLE telemetry ADD COLUMN {column_name} {column_definition}"
                    )

                    # Add index for the new column
                    index_name = f"idx_telemetry_{column_name}"
                    cursor.execute(
                        f"CREATE INDEX IF NOT EXISTS {index_name} ON telemetry({column_name})"
                    )

            logger.debug("Column verification completed")

        except Exception as e:
            logger.error(f"Failed to ensure required columns: {e}")
            raise

    def add_telemetry(self, telemetry_data):
        """Add telemetry data to PostgreSQL database using JSON storage."""
        import json
        from interfaces.types import NodeData

        with self.lock:
            try:
                with self._get_connection() as conn:
                    with conn.cursor() as cursor:
                        # Get stats JSON - it should already be populated
                        stats_json = telemetry_data.stats_json or {}
                        if not NodeData.validate_stats_integrity(stats_json):
                            logger.warning(
                                f"Invalid stats data for hotkey {telemetry_data.hotkey}, storing anyway"
                            )

                        cursor.execute(
                            """
                            INSERT INTO telemetry (
                                hotkey, uid, boot_time, last_operation_time, 
                                "current_time", worker_id, stats_json
                            ) VALUES (
                                %s, %s, %s, %s, %s, %s, %s
                            )
                            """,
                            (
                                telemetry_data.hotkey,
                                telemetry_data.uid,
                                telemetry_data.boot_time,
                                telemetry_data.last_operation_time,
                                telemetry_data.current_time,
                                telemetry_data.worker_id,
                                json.dumps(stats_json),
                            ),
                        )
                        conn.commit()
                        logger.debug(
                            f"Added telemetry to PostgreSQL for hotkey: "
                            f"{telemetry_data.hotkey}"
                        )
            except psycopg2.Error as e:
                logger.error(f"Failed to add telemetry to PostgreSQL: {e}")
                raise

    def clean_old_entries(self, hours):
        """Remove telemetry entries older than specified hours."""
        with self.lock:
            try:
                with self._get_connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute(
                            """
                            DELETE FROM telemetry 
                            WHERE created_at < NOW() - INTERVAL '%s hours'
                            """,
                            (hours,),
                        )
                        rows_deleted = cursor.rowcount
                        conn.commit()
                        logger.info(
                            f"Cleaned {rows_deleted} old telemetry "
                            f"entries from PostgreSQL"
                        )
                        return rows_deleted
            except psycopg2.Error as e:
                logger.error(
                    f"Failed to clean old telemetry entries from " f"PostgreSQL: {e}"
                )
                raise

    def _convert_row_to_nodedata(self, row):
        """Convert a database row to NodeData object."""
        import json
        from interfaces.types import NodeData

        try:
            # Parse stats_json if it exists
            stats_json = (
                json.loads(row.get("stats_json", "{}")) if row.get("stats_json") else {}
            )

            # Create NodeData with JSON stats
            node_data = NodeData(
                hotkey=row["hotkey"],
                uid=row["uid"] or "",
                worker_id=row["worker_id"] or "",
                timestamp=int(row.get("timestamp", 0)) if row.get("timestamp") else 0,
                boot_time=row.get("boot_time", 0) or 0,
                last_operation_time=row.get("last_operation_time", 0) or 0,
                current_time=row.get("current_time", 0) or 0,
                stats_json=stats_json,
            )

            # Populate legacy fields for backward compatibility
            node_data.populate_legacy_fields()

            return node_data
        except Exception as e:
            logger.error(f"Failed to convert row to NodeData: {e}")
            # Return a default NodeData object with minimal data
            return NodeData(
                hotkey=row.get("hotkey", ""),
                uid=row.get("uid", ""),
                worker_id=row.get("worker_id", ""),
                timestamp=0,
                boot_time=0,
                last_operation_time=0,
                current_time=0,
                stats_json={},
            )

    def get_telemetry_by_hotkey(self, hotkey):
        """Retrieve telemetry data for a specific hotkey."""
        with self.lock:
            try:
                with self._get_connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute(
                            """
                            SELECT * FROM telemetry 
                            WHERE hotkey = %s 
                            ORDER BY created_at DESC
                            """,
                            (hotkey,),
                        )
                        rows = cursor.fetchall()
                        return [self._convert_row_to_nodedata(row) for row in rows]
            except psycopg2.Error as e:
                logger.error(
                    f"Failed to get telemetry by hotkey from " f"PostgreSQL: {e}"
                )
                return []

    def get_all_hotkeys_with_telemetry(self):
        """Retrieve all unique hotkeys that have telemetry entries."""
        with self.lock:
            try:
                with self._get_connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute(
                            """
                            SELECT DISTINCT hotkey FROM telemetry
                            """
                        )
                        return [row["hotkey"] for row in cursor.fetchall()]
            except psycopg2.Error as e:
                logger.error(
                    f"Failed to get hotkeys with telemetry from " f"PostgreSQL: {e}"
                )
                return []

    def delete_telemetry_by_hotkey(self, hotkey):
        """Delete all telemetry entries for a specific hotkey."""
        with self.lock:
            try:
                with self._get_connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute(
                            """
                            DELETE FROM telemetry WHERE hotkey = %s
                            """,
                            (hotkey,),
                        )
                        rows_deleted = cursor.rowcount
                        conn.commit()
                        logger.info(
                            f"Deleted {rows_deleted} telemetry entries "
                            f"for hotkey: {hotkey}"
                        )
                        return rows_deleted
            except psycopg2.Error as e:
                logger.error(
                    f"Failed to delete telemetry by hotkey from " f"PostgreSQL: {e}"
                )
                return 0

    def get_all_telemetry(self, limit=1000):
        """Retrieve all telemetry data from PostgreSQL database."""
        with self.lock:
            try:
                with self._get_connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute(
                            """
                            SELECT * FROM telemetry 
                            ORDER BY created_at DESC 
                            LIMIT %s
                            """,
                            (limit,),
                        )
                        rows = cursor.fetchall()
                        return [self._convert_row_to_nodedata(row) for row in rows]
            except psycopg2.Error as e:
                logger.error(f"Failed to get all telemetry from PostgreSQL: {e}")
                return []

    def get_telemetry_stats(self):
        """Get statistics about telemetry data."""
        with self.lock:
            try:
                with self._get_connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute(
                            """
                            SELECT 
                                COUNT(*) as total_entries,
                                COUNT(DISTINCT hotkey) as unique_hotkeys,
                                MIN(created_at) as oldest_entry,
                                MAX(created_at) as newest_entry
                            FROM telemetry
                            """
                        )
                        result = cursor.fetchone()
                        return {
                            "total_entries": result["total_entries"],
                            "unique_hotkeys": result["unique_hotkeys"],
                            "oldest_entry": (
                                result["oldest_entry"].isoformat()
                                if result["oldest_entry"]
                                else None
                            ),
                            "newest_entry": (
                                result["newest_entry"].isoformat()
                                if result["newest_entry"]
                                else None
                            ),
                        }
            except psycopg2.Error as e:
                logger.error(f"Failed to get telemetry stats from PostgreSQL: {e}")
                return {
                    "total_entries": 0,
                    "unique_hotkeys": 0,
                    "oldest_entry": None,
                    "newest_entry": None,
                }

    def check_connection(self):
        """Check if the database connection is working."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    return True
        except Exception as e:
            logger.error(f"PostgreSQL connection check failed: {e}")
            return False
