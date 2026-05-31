import sqlite3
from datetime import datetime
from config import DATABASE_PATH, SUBJECTS

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DATABASE_PATH)
        self.cursor = self.conn.cursor()
        self.create_tables()
    
    def create_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS study_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT NOT NULL,
                subject TEXT NOT NULL,
                minutes INTEGER NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS total_study_time (
                user_id INTEGER NOT NULL,
                username TEXT NOT NULL,
                subject TEXT NOT NULL,
                total_minutes INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, subject)
            )
        ''')
        
        self.conn.commit()
    
    def add_study_time(self, user_id, username, subject, minutes):
        if subject not in SUBJECTS:
            return False, f"Invalid subject. Available subjects: {', '.join(SUBJECTS.keys())}"
        
        if minutes <= 0:
            return False, "Minutes must be positive"
        
        try:
            self.cursor.execute('''
                INSERT INTO study_sessions (user_id, username, subject, minutes, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, username, subject, minutes, datetime.now()))
            
            self.cursor.execute('''
                INSERT INTO total_study_time (user_id, username, subject, total_minutes)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, subject) 
                DO UPDATE SET 
                    total_minutes = total_minutes + ?,
                    username = ?
            ''', (user_id, username, subject, minutes, minutes, username))
            
            self.conn.commit()
            return True, f"Added {minutes} minutes to {subject}"
        
        except Exception as e:
            return False, f"Database error: {str(e)}"
    
    def remove_study_time(self, user_id, subject, minutes):
        if subject not in SUBJECTS:
            return False, f"Invalid subject. Available subjects: {', '.join(SUBJECTS.keys())}"
        
        if minutes <= 0:
            return False, "Minutes must be positive"
        
        try:
            self.cursor.execute('''
                SELECT total_minutes FROM total_study_time
                WHERE user_id = ? AND subject = ?
            ''', (user_id, subject))
            
            result = self.cursor.fetchone()
            
            if not result or result[0] < minutes:
                return False, f"Insufficient study time. You only have {result[0] if result else 0} minutes in {subject}"
            
            self.cursor.execute('''
                INSERT INTO study_sessions (user_id, username, subject, minutes, timestamp)
                VALUES (?, (SELECT username FROM total_study_time WHERE user_id = ? LIMIT 1), ?, ?, ?)
            ''', (user_id, user_id, subject, -minutes, datetime.now()))
            
            self.cursor.execute('''
                UPDATE total_study_time
                SET total_minutes = total_minutes - ?
                WHERE user_id = ? AND subject = ?
            ''', (minutes, user_id, subject))
            
            self.conn.commit()
            return True, f"Removed {minutes} minutes from {subject}"
        
        except Exception as e:
            return False, f"Database error: {str(e)}"
    
    def get_user_progress(self, user_id, username):
        self.cursor.execute('''
            SELECT subject, total_minutes 
            FROM total_study_time 
            WHERE user_id = ?
            ORDER BY total_minutes DESC
        ''', (user_id,))
        
        results = self.cursor.fetchall()
        
        if not results:
            self._ensure_user_exists(user_id, username)
            results = []
        
        return results
    
    def get_leaderboard(self):
        self.cursor.execute('''
            SELECT 
                username,
                SUM(total_minutes) as total_time
            FROM total_study_time
            GROUP BY user_id, username
            ORDER BY total_time DESC
            LIMIT 10
        ''')
        
        return self.cursor.fetchall()
    
    def _ensure_user_exists(self, user_id, username):
        for subject in SUBJECTS.keys():
            self.cursor.execute('''
                INSERT OR IGNORE INTO total_study_time (user_id, username, subject, total_minutes)
                VALUES (?, ?, ?, 0)
            ''', (user_id, username, subject))
        self.conn.commit()
    
    def close(self):
        self.conn.close()