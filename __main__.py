"""A Python Pulumi program"""
import pulumi

import pulumi_digitalocean as do
from pulumi_kubernetes import Provider
from pulumi_kubernetes.core import v1 as core
from pulumi_kubernetes.apps.v1 import Deployment
from pulumi_kubernetes.apps.v1 import DeploymentSpecArgs
from pulumi_kubernetes.meta.v1 import LabelSelectorArgs, ObjectMetaArgs


config = pulumi.Config()
region = config.require('region')
db = config.require_object('db')
cluster = config.require_object('cluster')

db = do.Droplet(
	db['name'],
	image=db['image'],
	region=region,
	name=db['name'],
	size=db['size']
)
#node_pool = do.KubernetesNodePool(
#	name='workers',
#	size=DropletSlug.DROPLET_S1_VCPU2_GB,
#	node_count=3
#)

cluster = do.KubernetesCluster(
	cluster['name'],
	name=cluster['name'],
	region=region,
	version=cluster['version'],
	node_pool=do.KubernetesClusterNodePoolArgs(
		name=cluster['base_node_pool']['name'],
		size=cluster['base_node_pool']['size'],
		node_count=cluster['base_node_pool']['node_count']
	)
)
kube_config = cluster.kube_configs[0].raw_config.apply(lambda x: x)
k8s_provider = Provider("do-k8s", kubeconfig=kube_config)

app_labels = {"app": "app-nginx"}
app = Deployment(
	'do-app-dep',
	spec=DeploymentSpecArgs(
		selector=LabelSelectorArgs(match_labels=app_labels),
		replicas=1,
		template=core.PodTemplateSpecArgs(
			metadata=ObjectMetaArgs(labels=app_labels),
			spec=core.PodSpecArgs(
				containers=[
					core.ContainerArgs(name='nginx', image='nginx')
				]
			),
		),
	),
	opts=pulumi.ResourceOptions(provider=k8s_provider)
)

ingress = core.Service(
	'do-app-svc',
	spec=core.ServiceSpecArgs(
		type='LoadBalancer',
		selector=app_labels,
		ports=[core.ServicePortArgs(port=80)],
	),
	opts=pulumi.ResourceOptions(
		provider=k8s_provider,
		custom_timeouts=pulumi.CustomTimeouts(
			create="15m",
			delete="15m"
		)
	)
)

ingress_ip = ingress.status.apply(lambda s: s.load_balancer.ingress[0].ip)


pulumi.export('db', db)
pulumi.export('cluster', cluster)
pulumi.export('ingress_ip', ingress_ip)
pulumi.export('kube_config', kube_config)
