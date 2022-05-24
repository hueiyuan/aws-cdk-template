from aws_cdk import (
    Stack,
    CfnTag,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_elasticloadbalancingv2 as elbv2,
    aws_route53 as route53,
    aws_elasticache as elasticache,
    aws_rds as rds,
    aws_secretsmanager as secretsmanager
)
from constructs import Construct

from configs import general_config, redash_config

CDK_GENERAL_CONF = general_config.GeneralConfig()
CDK_REDASH_CONF = redash_config.RedashConfig

with open(CDK_REDASH_CONF.user_data_shell_path) as f:
    redash_user_data = f.read()

class CdkRedashStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, environment:str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        redis_name = f'redash-redis-{environment}'
        postgresql_name = f'redash-postgresql-{environment}'
        redash_service_name = f'redash-{environment}'
        redash_instance_profile_name = f'redash-instance-profile-{environment}'
        redash_target_group_name = f'redash-target_group-{environment}'
        redash_dns = f'redash-{environment}.com'
        
        redash_redis = elasticache.CfnCacheCluster(self, f"RedashRedisCluster-{environment}",
            cluster_name = redis_name,
            vpc_security_group_ids = CDK_GENERAL_CONF.security_group,
            engine = CDK_REDASH_CONF.redis['engine'],
            engine_version = CDK_REDASH_CONF.redis['engine_version'],
            port = 6379,
            num_cache_nodes = CDK_REDASH_CONF.redis['number_cache_nodes'],
            cache_node_type = CDK_REDASH_CONF.redis['node_type'],
            cache_subnet_group_name = 'in-default-all-vpc',
            tags=[
                CfnTag(key='Name',value=redash_service_name),
                CfnTag(key='Cost',value='infra'),
                CfnTag(key='Environment',value=environment)
            ]
        )
        
        master_secret = secretsmanager.Secret.from_secret_name_v2(self, f'ImportedRedashDBSecret-{environment}',
            secret_name=CDK_REDASH_CONF.secret_name
        )
        
        redash_postgres_db = rds.CfnDBInstance(self, f"RedashPostgresDB-{environment}",
            db_instance_class = CDK_REDASH_CONF.postgres_db['db_instance_type'],
            allocated_storage = CDK_REDASH_CONF.postgres_db['db_allocated_storage'],
            backup_retention_period = CDK_REDASH_CONF.postgres_db['backup_retention_period'],
            db_instance_identifier = postgresql_name,
            db_name = CDK_REDASH_CONF.postgres_db['db_name'],
            db_subnet_group_name = 'default-postgresql',
            engine = CDK_REDASH_CONF.postgres_db['engine'],
            engine_version = CDK_REDASH_CONF.postgres_db['engine_version'],
            vpc_security_groups = CDK_GENERAL_CONF.security_group,
            master_username = master_secret.secret_value_from_json('username').to_string(),
            master_user_password = master_secret.secret_value_from_json('password').to_string(),
            multi_az = False,
            publicly_accessible = False,
            storage_type = 'gp2',
            tags=[
                CfnTag(key='Name',value=redash_service_name),
                CfnTag(key='Cost',value='infra'),
                CfnTag(key='Environment',value=environment)
            ]
        )
        
        redash_iam_role = iam.CfnRole(self, f'RedashRole-{environment}',
            path='/',
            managed_policy_arns = [
                'arn:aws:iam::aws:policy/AmazonRedshiftReadOnlyAccess',
                'arn:aws:iam::aws:policy/CloudWatchFullAccess'
            ],
            policies=[
                iam.CfnRole.PolicyProperty(
                    policy_name="RedashRDSPolicy",
                    policy_document={
                        'Version': '2012-10-17',
                        'Statement': [
                            {
                                'Sid': '',
                                'Effect': 'Allow',
                                'Action': [
                                    'rds.*'
                                ],
                                'resource': 'arn:aws:rds:ap-northeast-1:473024607515:db:redash-staging'
                            }
                        ]
                    }
                ),
                iam.CfnRole.PolicyProperty(
                    policy_name="RedashRedisPolicy",
                    policy_document={
                        'Version': '2012-10-17',
                        'Statement': [
                            {
                                'Sid': '',
                                'Effect': 'Allow',
                                'Action': [
                                    'elasticache.*'
                                ],
                                'resource': 'arn:aws:elasticache:ap-northeast-1:473024607515:cluster:redash-staging'
                            }
                        ]
                    }
                )
            ],
            assume_role_policy_document={
                'Version': '2012-10-17',
                'Statement': [
                    {
                        'Sid': '',
                        'Effect': 'Allow',
                        'Principal': {
                            'Service': [
                                'ec2.amazonaws.com'
                            ]
                        },
                        'Action': [
                            'sts:AssumeRole'
                        ]
                    }
                ]
            },
        )
        
        redash_instance_profile = iam.CfnInstanceProfile(self, f'RedashInstanceProfile-{environment}',
            instance_profile_name=redash_instance_profile_name,
            roles = [redash_iam_role.ref]
        )
        
        redash_instance = ec2.CfnInstance(self, f'RedashInstance-{environment}',
            instance_type=CDK_REDASH_CONF.instance_type,
            key_name=CDK_GENERAL_CONF.ec2_key_name,
            subnet_id=CDK_GENERAL_CONF.subnet_ids[0],
            security_group_ids=CDK_GENERAL_CONF.security_group,
            image_id=CDK_REDASH_CONF.ami[environment],
            iam_instance_profile=redash_instance_profile.ref,
            tags=[
                CfnTag(key='Name',value=redash_service_name),
                CfnTag(key='Cost',value='infra'),
                CfnTag(key='Environment',value=environment)
            ],
            block_device_mappings=[ec2.CfnInstance.BlockDeviceMappingProperty(
                device_name="/dev/sda1",
                ebs=ec2.CfnInstance.EbsProperty(
                    delete_on_termination=True,
                    volume_size=10,
                    volume_type="gp2"
                )
            )],
            user_data=redash_user_data
        )
        
        redash_target_group = elbv2.CfnTargetGroup(self, f'RedashTargetGroup-{environment}',
            name=redash_target_group_name,
            port=CDK_REDASH_CONF.service_port,
            protocol='HTTP',
            protocol_version='HTTP1',
            target_type='instance',
            targets=[
                elbv2.CfnTargetGroup.TargetDescriptionProperty(
                    id=redash_instance.ref,
                    port=CDK_REDASH_CONF.service_port
                )
            ],
            vpc_id=CDK_GENERAL_CONF.vpc_id,
            target_group_attributes=[
                elbv2.CfnTargetGroup.TargetGroupAttributeProperty(
                    key='load_balancing.algorithm.type',
                    value=CDK_REDASH_CONF.target_group_lb,
                )
            ],
            tags=[
                CfnTag(key='Name',value=redash_service_name),
                CfnTag(key='Cost',value='infra'),
                CfnTag(key='Environment',value=environment)
            ]
        )
        
        redash_dns_record = route53.CfnRecordSet(self, f'RedashRecordSet-{environment}',
            hosted_zone_id=CDK_REDASH_CONF.private_zone_id,
            name=redash_dns,
            type='A',
            alias_target=route53.CfnRecordSet.AliasTargetProperty(
                dns_name=CDK_REDASH_CONF.recordset_dns_name,
                hosted_zone_id=CDK_REDASH_CONF.etl_alb_zone_id,
                evaluate_target_health=False
            ),
        )
        
        redash_listener_rule = elbv2.CfnListenerRule(self, f'RedashListenerRule-{environment}',
            priority=1,
            listener_arn=CDK_REDASH_CONF.linstener_arn,
            actions = [
                elbv2.CfnListenerRule.ActionProperty(
                    type='forward',
                    target_group_arn=redash_target_group.ref
                )
            ],
            conditions = [
                elbv2.CfnListenerRule.RuleConditionProperty(
                    field='host-header',
                    host_header_config = elbv2.CfnListenerRule.HostHeaderConfigProperty(
                        values=[redash_dns_record.ref]
                    ),
                )
            ]
        )
    
