import pulumi
import pulumi_docker as docker
import pulumi_kubernetes as k8s
from infra.providers.k3d import K3dCluster
from pulumi_kubernetes.core import v1 as core
from pulumi_kubernetes.helm import v3 as helm

config = pulumi.Config()


cluster_cfg = config.require_object('k3d_config')
cluster = K3dCluster(
	cluster_cfg['name'],
	cluster_cfg,
	opts=pulumi.ResourceOptions(additional_secret_outputs=['kubeconfig'])
)
kubeconfig = cluster.kubeconfig.apply(lambda x: x)
k8s_provider = k8s.Provider(
	'k3d-provider',
	kubeconfig=kubeconfig,
	opts=pulumi.ResourceOptions(
		parent=cluster
	)
)

cluster_name = config.require('cluster_name')
network_name = f'k3d-{cluster_name}'
registry_image = docker.RemoteImage(
	'registry-image',
	keep_locally=True,
	name='registry:2'
)
registry_container = docker.Container(
	'registry-container',
	image=registry_image.latest,
	name='k3d-registry',
	ports=[
		docker.ContainerPortArgs(
			internal=5000,
			external=5000
		)
	],
	networks_advanced=[
		docker.ContainerNetworksAdvancedArgs(
			name=network_name,
		)
	],
	opts=pulumi.ResourceOptions(
		parent=registry_image
	)
)

db_cfg = config.require_object('db')
db_image = docker.RemoteImage(
	'rethink-image',
	keep_locally=True,
	name=db_cfg['image']
)
db_container = docker.Container(
	'rethink-container',
	image=db_image.latest,
	name='rethink-db',
	ports=[
		docker.ContainerPortArgs(
			internal=28015,
			external=28015
		)
	],
	opts=pulumi.ResourceOptions(
		parent=db_image
	)
)


def omit_crd_status(obj, opts):
	if obj['kind'] == 'CustomResourceDefinition':
		obj.pop('status')


traefik_ns = core.Namespace(
	'traefik-namespace',
	metadata={'name': 'traefik'},
	opts=pulumi.ResourceOptions(
		parent=cluster,
		provider=k8s_provider
	)
)
ingress = helm.Chart(
	'traefik-helm',
	helm.ChartOpts(
		skip_await=True,
		namespace='traefik',
		version='1.87.2',
		chart='traefik',
		values={'rbac': {'enabled': True}},
		transformations=[omit_crd_status],
		fetch_opts=helm.FetchOpts(
			repo='https://charts.helm.sh/stable'
		)
	),
	opts=pulumi.ResourceOptions(
		parent=cluster,
		provider=k8s_provider,
		depends_on=[traefik_ns]
	)
)

# K3S installs metrics-server by default
#metrics = helm.Chart(
#	'metrics-server',
#	helm.ChartOpts(
#		skip_await=True,
#		namespace='kube-system',
#		chart='metrics-server',
#		fetch_opts=helm.FetchOpts(
#			repo='https://charts.bitnami.com/bitnami'
#		)
#	),
#	opts=pulumi.ResourceOptions(
#		parent=cluster,
#		provider=k8s_provider,
#		depends_on=[cluster]
#	)
#)

exports = {
	'db-name': db_container.name,
	'cluster-name': cluster.name,
	'kubeconfig': cluster.kubeconfig
	#'cluster_role_binding': cluster_role_binding,
}
