"""A Python Pulumi program"""

import pulumi

import pulumi_digitalocean as do
from pulumi_digitalocean import Region
from pulumi_digitalocean import DropletSlug
from pulumi_digitalocean import KubernetesCluster
from pulumi_digitalocean import KubernetesNodePool

config = pulumi.Config()
region = config.require('region')
db = config.require_object('db')
cluster = config.require_object('cluster')
#print(f'region: {region}')
#print(f'db: {db}')

db = do.Droplet(
	db['name'],
	image=db['image'],
	region=region,
	name=db['name'],
	size=db['size']
)
#node_pool = KubernetesNodePool(
#	name='workers',
#	size=DropletSlug.DROPLET_S1_VCPU2_GB,
#	node_count=3
#)

cluster = KubernetesCluster(
	cluster['name'],
	name=cluster['name'],
	region=region,
	version=cluster['version'],
	node_pool=cluster['base_node_pool']
)
kube_config = cluster.kube_configs[0].raw_config.apply(lambda x: x)
pulumi.export('db', db)
pulumi.export('cluster', cluster)
pulumi.export('kube_config', kube_config)
