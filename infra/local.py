import pulumi
import pulumi_docker as docker
from infra.kind import KindCluster

config = pulumi.Config()


def create_local_cluster():
	cluster_cfg = config.require_object('cluster')
	cluster = KindCluster(cluster_cfg['name'])
	return cluster


def create_local_db():
	db_cfg = config.require_object('db')
	image = docker.RemoteImage(
		'rethink',
		keep_locally=True,
		name=db_cfg['image']
	)
	container = docker.Container(
		'rethink-container',
		image=image.latest,
		ports=[
			docker.ContainerPortArgs(
				internal=28015,
				external=28015
			)
		],
	)
	return container


def create_local_env():
	cluster = create_local_cluster()
	db = create_local_db()

	pulumi.export('db', db)
	pulumi.export('cluster', cluster)
