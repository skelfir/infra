import pulumi

import pulumi_kubernetes as k8s
import pulumi_digitalocean as do
from pulumi_kubernetes.core import v1 as core
from pulumi_kubernetes.apps import v1 as apps
from pulumi_kubernetes.meta import v1 as meta

config = pulumi.Config()


def create_cloud_db():
	db_cfg = config.require_object('db')
	db = do.Droplet(
		db_cfg['name'],
		image=db_cfg['image'],
		region=config.require('region'),
		name=db_cfg['name'],
		size=db_cfg['size']
	)
	return db


def create_worker_node_pool():
	cluster_cfg = config.require_object('cluster')
	node_pool = do.KubernetesNodePool(
		name=cluster_cfg['worker_node_pool']['name'],
		size=cluster_cfg['worker_node_pool']['size'],
		node_count=3
	)
	return node_pool


def create_cloud_cluster():
	cluster_cfg = config.require_object('cluster')
	cluster = do.KubernetesCluster(
		cluster_cfg['name'],
		name=cluster_cfg['name'],
		region=config.require('region'),
		version=cluster_cfg['version'],
		node_pool=do.KubernetesClusterNodePoolArgs(
			name=cluster_cfg['base_node_pool']['name'],
			size=cluster_cfg['base_node_pool']['size'],
			node_count=cluster_cfg['base_node_pool']['node_count']
		)
	)
	return cluster


def create_nginx_app(k8s_provider):
	app_labels = {"app": "app-nginx"}
	app = apps.Deployment(
		'do-app-dep',
		spec=apps.DeploymentSpecArgs(
			selector=meta.LabelSelectorArgs(match_labels=app_labels),
			replicas=1,
			template=core.PodTemplateSpecArgs(
				metadata=meta.ObjectMetaArgs(labels=app_labels),
				spec=core.PodSpecArgs(
					containers=[
						core.ContainerArgs(name='nginx', image='nginx')
					]
				),
			),
		),
		opts=pulumi.ResourceOptions(provider=k8s_provider)
	)
	return app


def create_ingress(k8s_provider):
	app_labels = {"app": "app-nginx"}
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
	return ingress


def create_cloud_env():
	db = create_cloud_db()
	cluster = create_cloud_cluster()
	kube_config = cluster.kube_configs[0].raw_config.apply(lambda x: x)
	k8s_provider = k8s.Provider("do-k8s", kubeconfig=kube_config)
	app = create_nginx_app(k8s_provider)
	ingress = create_ingress(k8s_provider)
	ingress_ip = ingress.status.apply(lambda s: s.load_balancer.ingress[0].ip)

	pulumi.export('db', db)
	pulumi.export('app', app.id)
	pulumi.export('cluster', cluster)
	pulumi.export('ingress_ip', ingress_ip)
	pulumi.export('kube_config', kube_config)
