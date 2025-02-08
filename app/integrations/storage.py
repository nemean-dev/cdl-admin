import os
import boto3
import json
import pandas as pd
from io import StringIO
from flask import current_app
from typing import Any

class StorageService:    
    def __init__(self):
        self.use_local_storage = current_app.config.get('USE_LOCAL_STORAGE', False)
        self.local_storage_path = './local_data'

        if not self.use_local_storage:
            self.client = boto3.client(
                's3',
                aws_access_key_id=current_app.config['AWS_ACCESS_KEY'],
                aws_secret_access_key=current_app.config['AWS_SECRET_KEY'],
                region_name=current_app.config['AWS_REGION']
            )
            self.bucket_name = current_app.config['AWS_BUCKET_NAME']

    def _get_local_path(self, key: str) -> str:
        '''Returns the full local file path for a given key.'''
        return os.path.join(self.local_storage_path, key)

    def upload_text(self, key: str, text: str) -> None:
        '''Uploads plain text to storage.'''
        if self.use_local_storage:
            with open(self._get_local_path(key), 'w', encoding='utf-8') as f:
                f.write(text)
        else:
            self.client.put_object(Bucket=self.bucket_name, Key=key, Body=text)

    def download_text(self, key: str) -> str:
        '''Downloads plain text from storage.'''
        if self.use_local_storage:
            with open(self._get_local_path(key), 'r', encoding='utf-8') as f:
                return f.read()
        else:
            obj = self.client.get_object(Bucket=self.bucket_name, Key=key)
            return obj['Body'].read().decode('utf-8')

    def upload_json(self, key: str, data: Any) -> None:
        '''Uploads JSON data to storage.'''
        self.upload_text(key, json.dumps(data, indent=4))

    def download_json(self, key: str) -> Any:
        '''Downloads JSON data from storage.'''
        return json.loads(self.download_text(key))

    def upload_csv(self, key: str, df: pd.DataFrame) -> None:
        '''Uploads a Pandas DataFrame as a CSV to storage.'''
        csv_buffer = StringIO()
        df.to_csv(csv_buffer, index=False)
        self.upload_text(key, csv_buffer.getvalue())

    def download_csv(self, key: str) -> pd.DataFrame:
        '''Downloads a CSV from storage into a Pandas DataFrame.'''
        csv_data = self.download_text(key)
        return pd.read_csv(StringIO(csv_data))
