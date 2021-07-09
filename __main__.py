import pulumi
from infra.local import create_local_env
from infra.cloud import create_cloud_env

stack = pulumi.get_stack()

if stack == 'local':
	create_local_env()
else:
	create_cloud_env()
