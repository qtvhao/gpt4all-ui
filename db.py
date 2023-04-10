
import sqlite3
# =================================== Database ==================================================================
class DiscussionsDB:
    MSG_TYPE_NORMAL         = 0
    MSG_TYPE_CONDITIONNING  = 1

    def __init__(self, db_path="database.db"):
        self.db_path = db_path

    def populate(self):
        """
        create database schema
        """
        print("Checking discussions database...")
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Check if the 'schema_version' table exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version INTEGER NOT NULL
                )
            """)
            discussion_table_exist=False
            message_table_exist=False
            try:
                cursor.execute("""
                        CREATE TABLE discussion (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            title TEXT
                        )
                    """)
            except:
                discussion_table_exist=True        
            try:
                cursor.execute("""
                        CREATE TABLE IF NOT EXISTS message (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            sender TEXT NOT NULL,
                            content TEXT NOT NULL,
                            type INT NOT NULL,
                            rank INT NOT NULL,
                            discussion_id INTEGER NOT NULL,
                            FOREIGN KEY (discussion_id) REFERENCES discussion(id)
                        )
                    """
                    )
            except :
                message_table_exist=True

            # Get the current version from the schema_version table
            cursor.execute("SELECT version FROM schema_version WHERE id = 1")
            row = cursor.fetchone()
            if row is None:
                # If the table is empty, assume version 0
                version = 0
            else:
                # Otherwise, use the version from the table
                version = row[0]

            # Upgrade the schema to version 1
            if version < 1:
                print("Upgrading schema to version 1...")
                # Add the 'created_at' column to the 'message' table
                if message_table_exist:
                    cursor.execute("ALTER TABLE message ADD COLUMN type INT DEFAULT 0")
                    cursor.execute("ALTER TABLE message ADD COLUMN rank INT DEFAULT 0")
                # Update the schema version
                cursor.execute("INSERT INTO schema_version (id, version) VALUES (1, 1)")
                version = 1
        
            conn.commit()

    def select(self, query, params=None, fetch_all=True):
        """
        Execute the specified SQL select query on the database,
        with optional parameters.
        Returns the cursor object for further processing.
        """
        with sqlite3.connect(self.db_path) as conn:
            if params is None:
                cursor = conn.execute(query)
            else:
                cursor = conn.execute(query, params)
            if fetch_all:
                return cursor.fetchall()
            else:
                return cursor.fetchone()
            

    def delete(self, query):
        """
        Execute the specified SQL delete query on the database,
        with optional parameters.
        Returns the cursor object for further processing.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            conn.commit()
   
    def insert(self, query, params=None):
        """
        Execute the specified INSERT SQL query on the database,
        with optional parameters.
        Returns the ID of the newly inserted row.
        """
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(query, params)
            rowid = cursor.lastrowid
            conn.commit()
        self.conn = None
        return rowid

    def update(self, query, params=None):
        """
        Execute the specified Update SQL query on the database,
        with optional parameters.
        Returns the ID of the newly inserted row.
        """
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(query, params)
            conn.commit()
    
    def load_last_discussion(self):
        last_discussion_id = self.select("SELECT id FROM discussion ORDER BY id DESC LIMIT 1", fetch_all=False)
        if last_discussion_id is None:
            last_discussion_id = self.create_discussion()
        else:
            last_discussion_id=last_discussion_id[0]
        return Discussion(last_discussion_id, self)
    
    def create_discussion(self, title="untitled"):
        """Creates a new discussion

        Args:
            title (str, optional): The title of the discussion. Defaults to "untitled".

        Returns:
            Discussion: A Discussion instance 
        """
        discussion_id = self.insert(f"INSERT INTO discussion (title) VALUES (?)",(title,))
        return Discussion(discussion_id, self)

    def build_discussion(self, discussion_id=0):
        return Discussion(discussion_id, self)

    def get_discussions(self):
        rows = self.select("SELECT * FROM discussion")         
        return [{"id": row[0], "title": row[1]} for row in rows]

    def does_last_discussion_have_messages(self):
        last_discussion_id = self.select("SELECT id FROM discussion ORDER BY id DESC LIMIT 1", fetch_all=False)
        if last_discussion_id is None:
            last_discussion_id = self.create_discussion()
        else:
            last_discussion_id=last_discussion_id[0]
        last_message = self.select("SELECT * FROM message WHERE discussion_id=?", (last_discussion_id,), fetch_all=False)
        return last_message is not None
    
    def remove_discussions(self):
        self.delete("DELETE FROM message")
        self.delete("DELETE FROM discussion")


    def export_to_json(self):
        db_discussions = self.select("SELECT * FROM discussion")
        discussions = []
        for row in db_discussions:
            discussion_id = row[0]
            discussion = {"id": discussion_id, "messages": []}
            rows = self.select(f"SELECT * FROM message WHERE discussion_id=?",(discussion_id))
            for message_row in rows:
                discussion["messages"].append(
                    {"sender": message_row[1], "content": message_row[2]}
                )
            discussions.append(discussion)
        return discussions


class Discussion:
    def __init__(self, discussion_id, discussions_db:DiscussionsDB):
        self.discussion_id = discussion_id
        self.discussions_db = discussions_db

    def add_message(self, sender, content, message_type=0, rank=0):
        """Adds a new message to the discussion

        Args:
            sender (str): The sender name
            content (str): The text sent by the sender

        Returns:
            int: The added message id
        """
        message_id = self.discussions_db.insert(
            "INSERT INTO message (sender, content, type, rank, discussion_id) VALUES (?, ?, ?, ?, ?)", 
            (sender, content, message_type, rank, self.discussion_id)
        )
        return message_id

    def rename(self, new_title):
        """Renames the discussion

        Args:
            new_title (str): The nex discussion name
        """
        self.discussions_db.update(
            f"UPDATE discussion SET title=? WHERE id=?",(new_title,self.discussion_id)
        )

    def delete_discussion(self):
        """Deletes the discussion
        """
        self.discussions_db.delete(
            f"DELETE FROM message WHERE discussion_id={self.discussion_id}"
        )
        self.discussions_db.delete(
            f"DELETE FROM discussion WHERE id={self.discussion_id}"
        )

    def get_messages(self):
        """Gets a list of messages information

        Returns:
            list: List of entries in the format {"id":message id, "sender":sender name, "content":message content, "type":message type, "rank": message rank}
        """
        rows = self.discussions_db.select(
            f"SELECT * FROM message WHERE discussion_id={self.discussion_id}"
        )
        return [{"id": row[0], "sender": row[1], "content": row[2], "type": row[3], "rank": row[4]} for row in rows]

    def update_message(self, message_id, new_content):
        """Updates the content of a message

        Args:
            message_id (int): The id of the message to be changed
            new_content (str): The nex message content
        """
        self.discussions_db.update(
            f"UPDATE message SET content = ? WHERE id = ?",(new_content,message_id)
        )
    
    def message_rank_up(self, message_id):
        """Increments the rank of the message

        Args:
            message_id (int): The id of the message to be changed
        """
        # Retrieve current rank value for message_id
        current_rank = self.discussions_db.select("SELECT rank FROM message WHERE id=?", (message_id,),False)[0]

        # Increment current rank value by 1
        new_rank = current_rank + 1        
        self.discussions_db.update(
            f"UPDATE message SET rank = ? WHERE id = ?",(new_rank,message_id)
        )
        return new_rank

    def message_rank_down(self, message_id):
        """Increments the rank of the message

        Args:
            message_id (int): The id of the message to be changed
        """
        # Retrieve current rank value for message_id
        current_rank = self.discussions_db.select("SELECT rank FROM message WHERE id=?", (message_id,),False)[0]

        # Increment current rank value by 1
        new_rank = current_rank - 1        
        self.discussions_db.update(
            f"UPDATE message SET rank = ? WHERE id = ?",(new_rank,message_id)
        )
        return new_rank

# ========================================================================================================================
