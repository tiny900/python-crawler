#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Secure S3 uploader script - NO HARDCODED CREDENTIALS
Function: Upload data files from current directory to S3, delete old S3 files
"""

import boto3
import os
import glob
import sys
from datetime import datetime
from botocore.exceptions import ClientError


# ========== 三种安全的配置方式 ==========

def get_aws_credentials():
    """
    获取 AWS 凭证的安全方式
    优先级：环境变量 > AWS配置文件 > IAM角色
    """

    # 方式1：从环境变量读取（推荐）
    access_key = os.environ.get('AWS_ACCESS_KEY_ID')
    secret_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
    bucket_name = os.environ.get('S3_BUCKET_NAME', 'checkitanalytics')

    # 方式2：从配置文件读取（如果环境变量不存在）
    if not access_key or not secret_key:
        try:
            # 尝试从 .env 文件加载
            from dotenv import load_dotenv
            load_dotenv()
            access_key = os.environ.get('AWS_ACCESS_KEY_ID')
            secret_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
        except ImportError:
            print("提示: 安装 python-dotenv 可以使用 .env 文件")

    # 方式3：使用 AWS 默认配置（~/.aws/credentials）
    # 如果都没有，boto3 会自动查找默认配置

    return access_key, secret_key, bucket_name


def create_s3_client(access_key=None, secret_key=None):
    """
    创建 S3 客户端
    如果没有提供密钥，将使用 AWS 默认配置
    """
    try:
        if access_key and secret_key:
            # 使用提供的密钥
            s3 = boto3.client(
                's3',
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key
            )
            print("使用环境变量中的 AWS 凭证")
        else:
            # 使用默认配置（~/.aws/credentials 或 IAM 角色）
            s3 = boto3.client('s3')
            print("使用 AWS 默认配置（~/.aws/credentials 或 IAM 角色）")

        # 测试连接
        s3.list_buckets()
        print("S3 连接成功")
        return s3

    except ClientError as e:
        print(f"S3 连接失败: {e}")
        print("\n请确保已配置 AWS 凭证，可以使用以下任一方式：")
        print("1. 设置环境变量: AWS_ACCESS_KEY_ID 和 AWS_SECRET_ACCESS_KEY")
        print("2. 创建 .env 文件（见 .env.example）")
        print("3. 运行 'aws configure' 配置 AWS CLI")
        print("4. 在 EC2 上使用 IAM 角色")
        return None


def upload_to_s3():
    """Upload data files to S3"""

    # 获取凭证
    access_key, secret_key, bucket_name = get_aws_credentials()

    print(f"Starting S3 upload - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Target bucket: {bucket_name}")

    # 创建 S3 客户端
    s3 = create_s3_client(access_key, secret_key)
    if not s3:
        return False

    # 1. Delete old data files from S3
    print("\nDeleting old data files from S3...")
    try:
        response = s3.list_objects_v2(
            Bucket=bucket_name,
            Prefix='smart_news/twitter/'
        )

        deleted_count = 0
        if 'Contents' in response:
            for obj in response['Contents']:
                file_name = obj['Key'].replace('smart_news/twitter/', '')

                # Only delete specific format data files
                # Format: account_YYYYMMDD_HHMMSS.json
                should_delete = (
                        '_' in file_name and  # Contains underscore
                        file_name.endswith('.json') and  # JSON file
                        len(file_name.split('_')) >= 3  # At least 3 parts
                )

                if should_delete:
                    s3.delete_object(Bucket=bucket_name, Key=obj['Key'])
                    print(f"  Deleted: {file_name}")
                    deleted_count += 1
                else:
                    print(f"  Kept: {file_name}")

        print(f"  Deleted {deleted_count} old data files")

    except ClientError as e:
        print(f"Failed to delete old files: {e}")
        # 继续上传，不因删除失败而停止

    # 2. Find local data files in twitter_data folder
    print("\nFinding local data files...")

    data_folder = 'twitter_data'
    if not os.path.exists(data_folder):
        print(f"Data folder not found: {data_folder}")
        # 尝试创建文件夹
        os.makedirs(data_folder, exist_ok=True)
        print(f"Created empty folder: {data_folder}")
        return False

    # Find all data files in twitter_data folder
    file_patterns = ['*.json', '*.txt', '*.csv']
    data_files = []

    for pattern in file_patterns:
        data_files.extend(glob.glob(os.path.join(data_folder, pattern)))

    if not data_files:
        print("No data files found")
        return False

    print(f"Found {len(data_files)} data files:")
    for file in data_files:
        size = os.path.getsize(file)
        print(f"  {os.path.basename(file)} ({size:,} bytes)")

    # 3. Upload new files to S3
    print("\nUploading files to S3...")

    uploaded_count = 0
    failed_count = 0

    for file_path in data_files:
        file_name = os.path.basename(file_path)  # Get filename only
        s3_key = f"smart_news/twitter/{file_name}"

        try:
            print(f"  Uploading: {file_name}")
            s3.upload_file(file_path, bucket_name, s3_key)
            print(f"  ✓ Success: {file_name}")
            uploaded_count += 1

        except ClientError as e:
            print(f"  ✗ Failed: {file_name} - {e}")
            failed_count += 1

    # 4. Show results
    print(f"\nUpload completed:")
    print(f"  Successful: {uploaded_count} files")
    print(f"  Failed: {failed_count} files")
    print(f"  S3 path: s3://{bucket_name}/smart_news/twitter/")
    print(f"  Completed at: {datetime.now().strftime('%H:%M:%S')}")

    # 5. Verify upload results
    if uploaded_count > 0:
        print("\nVerifying files in S3:")
        try:
            response = s3.list_objects_v2(
                Bucket=bucket_name,
                Prefix='smart_news/twitter/',
                MaxKeys=10  # 只显示最近10个文件
            )

            if 'Contents' in response:
                print("  Recent files in S3:")
                # 按时间排序
                files = sorted(response['Contents'],
                               key=lambda x: x['LastModified'],
                               reverse=True)[:10]

                for obj in files:
                    if not obj['Key'].endswith('/'):
                        file_name = obj['Key'].replace('smart_news/twitter/', '')
                        size = obj['Size']
                        modified = obj['LastModified'].strftime('%H:%M:%S')
                        print(f"    {file_name} ({size:,} bytes) - {modified}")
            else:
                print("  No files found in S3")

        except ClientError as e:
            print(f"  Error verifying S3 files: {e}")

    return failed_count == 0


def main():
    """主函数"""
    print("Secure S3 Upload Tool")
    print("=" * 40)

    # 检查环境配置
    if not os.environ.get('AWS_ACCESS_KEY_ID'):
        print("\n⚠️  警告: 未检测到 AWS_ACCESS_KEY_ID 环境变量")
        print("请先配置 AWS 凭证：")
        print("\n方式1 - 使用环境变量:")
        print("  export AWS_ACCESS_KEY_ID=your_key")
        print("  export AWS_SECRET_ACCESS_KEY=your_secret")
        print("  export S3_BUCKET_NAME=checkitanalytics")
        print("\n方式2 - 使用 .env 文件:")
        print("  创建 .env 文件并添加上述变量")
        print("\n方式3 - 使用 AWS CLI:")
        print("  aws configure")
        print("")

    # 执行上传
    success = upload_to_s3()

    if success:
        print("\n✓ All files uploaded successfully!")
        sys.exit(0)  # Success exit
    else:
        print("\n✗ Some files failed to upload")
        sys.exit(1)  # Failure exit


if __name__ == "__main__":
    main()