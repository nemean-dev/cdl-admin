import os
import json
import pandas as pd
import boto3
from io import StringIO
from botocore.exceptions import ClientError
from flask import current_app
from typing import Any

class StorageNotFoundError(Exception):
    '''Raised when a requested file or object is not found in storage.'''
    pass

class StorageService:    
    def __init__(self):
        self.use_local_storage = current_app.config.get('USE_LOCAL_STORAGE', False)
        self.data_path = current_app.config['DATA_DIR']

        if not self.use_local_storage:
            self.client = boto3.client(
                's3',
                aws_access_key_id=current_app.config['AWS_ACCESS_KEY'],
                aws_secret_access_key=current_app.config['AWS_SECRET_KEY'],
                region_name=current_app.config['AWS_REGION']
            )
            self.bucket_name = current_app.config['AWS_BUCKET_NAME']

    def _get_path_or_key(self, key: str) -> str:
        '''
        Returns the full local file path or full key for a given key. (starting 
        from the data directory)
        '''
        if key[0] == '/':
            key = key[1:]
        return os.path.join(self.data_path, key)

    def upload_text(self, key: str, text: str) -> None:
        '''Uploads plain text to storage.'''
        key = self._get_path_or_key(key)
        if self.use_local_storage:
            with open(key, 'w', encoding='utf-8') as f:
                f.write(text)
        else:
            self.client.put_object(Bucket=self.bucket_name, Key=key, Body=text)

    def download_text(self, key: str) -> str:
        '''Downloads plain text from storage.'''
        key = self._get_path_or_key(key)
        
        if self.use_local_storage:
            if not os.path.exists(key):
                raise StorageNotFoundError(f"File not found: {key}")
            with open(key, 'r', encoding='utf-8') as f:
                return f.read()
        
        else:
            try:
                obj = self.client.get_object(Bucket=self.bucket_name, Key=key)
                return obj['Body'].read().decode('utf-8')
            except ClientError as e:
                if e.response['Error']['Code'] == 'NoSuchKey':
                    raise StorageNotFoundError(f"S3 object not found: {key}")
                raise

    # TODO change all processes that require file deletion so that this is no 
    # longer necessary, then remove this method and any delete privileges from 
    # the AWS permissions.
    def delete(self, key: str) -> None:
        '''Deletes a file from storage.'''
        key = self._get_path_or_key(key)
        
        if self.use_local_storage:
            if os.path.exists(key):
                os.remove(key)
        else:
            self.client.delete_object(Bucket=self.bucket_name, Key=key)

    def upload_json(self, key: str, data: Any) -> None:
        '''Uploads JSON data to storage.'''
        key = self._get_path_or_key(key)
        self.upload_text(key, json.dumps(data, indent=4))

    def download_json(self, key: str) -> Any:
        '''Downloads JSON data from storage.'''
        key = self._get_path_or_key(key)
        return json.loads(self.download_text(key))

    def upload_csv(self, key: str, df: pd.DataFrame, index:bool=False) -> None:
        '''Uploads a Pandas DataFrame as a CSV to storage.'''
        key = self._get_path_or_key(key)
        csv_buffer = StringIO()
        df.to_csv(csv_buffer, index=index)
        self.upload_text(key, csv_buffer.getvalue())

    def download_csv(self, key: str) -> pd.DataFrame:
        '''Downloads a CSV from storage into a Pandas DataFrame.'''
        key = self._get_path_or_key(key)
        csv_data = self.download_text(key)
        return pd.read_csv(StringIO(csv_data))
    
    def upload_bytes(self, s3_key, data, content_type="application/octet-stream"):
        '''Upload in-memory data to S3.'''
        self.client.upload_fileobj(data, self.bucket_name, s3_key, ExtraArgs={"ContentType": content_type})
