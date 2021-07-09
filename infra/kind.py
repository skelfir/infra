import yaml
import subprocess
from typing import Optional

from pulumi import Output
from pulumi import ResourceOptions
from pulumi.dynamic import Resource
from pulumi.dynamic import CreateResult
from pulumi.dynamic import ResourceProvider

cluster_config_file = '/tmp/local-cluster-config.yml'
default_cluster_config = {
	'kind': 'Cluster',
	'apiVersion': 'kind.x-k8s.io/v1alpha4',
	'nodes': [
		{'role': 'control-plane'},
		{'role': 'worker'},
		{'role': 'worker'}
	]
}


def write_config():
	with open(f'{cluster_config_file}', 'w') as f:
		yaml.dump(default_cluster_config, f)


def run(command):
	p = subprocess.run(command.split(), check=True, capture_output=True)
	if p.returncode != 0:
		raise Exception()
	return p


def create_kind_cluster(name):
	command = 'kind create cluster --name {name} --config {cluster_config_file}'
	command = command.format(name=name, cluster_config_file=cluster_config_file)
	p = run(command)
	return p


def delete_kind_cluster(name):
	command = 'kind delete cluster --name {name}'
	command = command.format(name=name)
	p = run(command)
	return p


class KindProvider(ResourceProvider):
	def create(self, inputs):
		write_config()
		create_kind_cluster(inputs['name'])
		return CreateResult(inputs['name'], outs={'name': inputs['name']})

	def delete(self, id, inputs):
		delete_kind_cluster(inputs['name'])


class KindCluster(Resource):
	name: Output[str]

	def __init__(self, name: str, opts: Optional[ResourceOptions] = None):
		super().__init__(KindProvider(), name, {'name': name}, opts)
