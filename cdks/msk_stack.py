from aws_cdk import (
    Stack,
    aws_msk as msk
)
from constructs import Construct

from configs import general_config, msk_config

CDK_MSK_CONF = msk_config.MSKConfig()
CDK_GENERAL_CONF = general_config.GeneralConfig()

class CdkMSKStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, environment:str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        kafka_cluster_name = f'kafka-cluster-{environment}'
        
        etl_bronze_msk_cluster = msk.CfnCluster(self, f'MskCluster-{environment}f',
            cluster_name = kafka_cluster_name,
            kafka_version = CDK_MSK_CONF.kafka_version,
            number_of_broker_nodes =CDK_MSK_CONF.number_of_broker[environment],
            enhanced_monitoring = CDK_MSK_CONF.metrics_level,
            tags={
                'Name': kafka_cluster_name,
                'Cost': 'cost',
                'Environment': environment
            },
            broker_node_group_info = msk.CfnCluster.BrokerNodeGroupInfoProperty(
                broker_az_distribution='DEFAULT',
                instance_type = CDK_MSK_CONF.instance_type[environment],
                security_groups = CDK_GENERAL_CONF.security_group,
                client_subnets = CDK_GENERAL_CONF.subnet_ids,
                storage_info = msk.CfnCluster.StorageInfoProperty(
                    ebs_storage_info=msk.CfnCluster.EBSStorageInfoProperty(
                        volume_size=CDK_MSK_CONF.broker_volume_size[environment]
                    )
                )
            )
        )
        
