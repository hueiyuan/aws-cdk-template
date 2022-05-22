from aws_cdk import (
    Stack,
    CfnTag,
    aws_redshift as redshift,
    aws_secretsmanager as secretsmanager
)

from constructs import Construct

from configs import redsfhit_config, general_config

CDK_REDSHIFT_CONF = redsfhit_config.RedshiftConfig()
CDK_GENERAL_CONF = general_config.GeneralConfig()

class CdkRedshiftStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, environment:str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        """
          redshift + secret manger
        """
        
        redshift_cluster_name = f'redshift-{environment}'
        redshift_subnet_group_name = f'redshift-subnet-group-{environment}'
        
        master_secret = secretsmanager.Secret.from_secret_name_v2(self, f'ImportedRedsfhitSecret-{environment}',
            secret_name=CDK_REDSHIFT_CONF.secret_name
        )
        
        redshift_subnet_group = redshift.CfnClusterSubnetGroup(self, redshift_subnet_group_name,
            description=f'redshift cluster subnet group in {environment}',
            subnet_ids=CDK_GENERAL_CONF.subnet_ids
        )
        
        redsfhit_cluster = redshift.CfnCluster(self, redshift_cluster_name,
            cluster_identifier = redshift_cluster_name,
            cluster_subnet_group_name = redshift_subnet_group.ref,
            cluster_type = CDK_REDSHIFT_CONF.cluster_type,
            db_name = 'dev',
            master_username = master_secret.secret_value_from_json('username').to_string(),
            master_user_password = master_secret.secret_value_from_json('password').to_string(),
            node_type = CDK_REDSHIFT_CONF.node_type,
            number_of_nodes=CDK_REDSHIFT_CONF.number_of_nodes,
            vpc_security_group_ids = CDK_GENERAL_CONF.security_group,
            tags=[
                CfnTag(key='Name',value=redshift_cluster_name),
                CfnTag(key='Cost',value='infra'),
                CfnTag(key='Environment',value=environment)
            ]
        )
        
