import pulumi
import base64 as b64

import pulumi_kubernetes as k8s
import pulumi_digitalocean as do
from infra.misc.rkubelog import RKubelog
from pulumi_kubernetes.core import v1 as core
from pulumi_kubernetes.helm import v3 as helm

config = pulumi.Config()

#skelfir_vpc = do.Vpc(
#	"example",
#	ip_range="10.10.10.0/16",
#	region=config.require('region')
#)

#db_cfg = config.require_object('db')
#db = do.Droplet(
#	db_cfg['name'],
#	monitoring=True,
#	name=db_cfg['name'],
#	size=db_cfg['size'],
#	image=db_cfg['image'],
#	region=config.require('region'),
#)


#ingress_lb = do.LoadBalancer(
#	'ingress-loadbalancer',
#	name="skelfir-lb",
#	region=config.require('region'),
#	size="lb-small",
#	algorithm="round_robin",
#	forwarding_rule={
#		'entry_port': 80,
#		'entry_protocol': "http",
#
#		'target_port': 80,
#		'target_protocol': "http"
#	},
#
#	lifecycle={
#		ignore_changes = [
#			forwarding_rule,
#		]
#	},
#	#droplet_ids=[web.id]
#)


#cluster_cfg = config.require_object('cluster')
#base_node_pool = do.KubernetesNodePool(
#	auto_scale=True,
#	min_nodes=1,
#	max_nodes=cluster_cfg['base_node_pool']['node_count'],
#	name=cluster_cfg['base_node_pool']['name'],
#	size=cluster_cfg['base_node_pool']['size'],
#	node_count=cluster_cfg['base_node_pool']['node_count']
#)


cluster_cfg = config.require_object('cluster')
cluster = do.KubernetesCluster(
	cluster_cfg['name'],
	name=cluster_cfg['name'],
	region=cluster_cfg['region'],
	version=cluster_cfg['version'],
	node_pool={
		'auto_scale': True,
		'max_nodes': 2,
		'min_nodes': 1,
		'name': cluster_cfg['base_node_pool']['name'],
		'size': cluster_cfg['base_node_pool']['size'],
		'node_count': cluster_cfg['base_node_pool']['node_count']
	}
)
kube_config = cluster.kube_configs[0].raw_config.apply(lambda x: x)
k8s_provider = k8s.Provider(
	'do-k8s',
	kubeconfig=kube_config,
	opts=pulumi.ResourceOptions(
		parent=cluster
	)
)


def omit_crd_status(obj, opts):
	if obj['kind'] == 'CustomResourceDefinition':
		obj.pop('status')


ingress_ns = core.Namespace(
	'ingress-namespace',
	metadata={'name': 'traefik'},
	opts=pulumi.ResourceOptions(
		parent=cluster,
		depends_on=[cluster],
		provider=k8s_provider,
	)
)
ingress = helm.Chart(
	'traefik-helm',
	helm.ChartOpts(
		#skip_await=True,
		namespace=ingress_ns.metadata.name.apply(lambda x: x),
		version='1.87.2',
		chart='traefik',
		values={'rbac': {'enabled': True}},
		transformations=[omit_crd_status],
		fetch_opts=helm.FetchOpts(
			repo='https://charts.helm.sh/stable'
		)
	),
	opts=pulumi.ResourceOptions(
		parent=ingress_ns,
		provider=k8s_provider,
		depends_on=[ingress_ns],
		custom_timeouts=pulumi.CustomTimeouts(
			create="30m",
			delete="30m"
		)
	)
)

metrics = helm.Chart(
	'metrics-server',
	helm.ChartOpts(
		skip_await=True,
		namespace='kube-system',
		chart='metrics-server',
		version='3.8.2',
		values={
			'apiService': {
				'create': True
			},
			'replicas': 1,
			#'extraArgs': {
			#	'kubelet-insecure-tls': True,
			#	'kubelet-preferred-address-types': 'InternalIP'
			#}
		},
		fetch_opts=helm.FetchOpts(
			repo='https://kubernetes-sigs.github.io/metrics-server/'
		)
	),
	opts=pulumi.ResourceOptions(
		parent=cluster,
		provider=k8s_provider,
		depends_on=[cluster]
	)
)

#rkubelog = RKubelog(
#	'rkubelog',
#	token=config.require('loggly_token'),
#	opts=pulumi.ResourceOptions(
#		parent=cluster,
#		provider=k8s_provider,
#		depends_on=[cluster]
#	)
#)

ingress_status = ingress.resources['v1/Service:traefik/traefik-helm'].status
ingress_ip = ingress_status.apply(lambda s: s.load_balancer.ingress[0].ip)

# No need to do this when domain has
# already been registered with DigitalOcean
#domain = do.Domain(
#	"logileifs-domain",
#	name='logileifs.com',
#	#ip_address=ingress_ip.apply(lambda x: x),
#	opts=pulumi.ResourceOptions(
#		depends_on=[ingress]
#	)
#)

dev_subdomain = do.DnsRecord(
	'skelfir-dev-subdomain',
	domain='skelfir.com',
	name='dev',
	type="A",
	value=ingress_ip.apply(lambda x: x),
	opts=pulumi.ResourceOptions(
		parent=cluster,
		depends_on=[ingress]
	)
)

#db_subdomain = do.DnsRecord(
#	'db-dev-subdomain',
#	domain='skelfir.com',
#	name='db.dev',
#	type='A',
#	value=db.ipv4_address.apply(lambda x: x),
#	opts=pulumi.ResourceOptions(
#		parent=db,
#		depends_on=[db]
#	)
#)


exports = {
	#'db_ip': db.ipv4_address,
	#'app': app.id,
	#'cluster': cluster,
	#'ingress': ingress,
	#'ingress_res': ingress_res,
	#'ingress_status': ingress_status,
	'cluster_id': cluster.id,
	'ingress_ip': ingress_ip,
	'kube_config': kube_config,
	#'db_fqdn': db_subdomain.fqdn,
	'cluster_fqdn': dev_subdomain.fqdn,
}
