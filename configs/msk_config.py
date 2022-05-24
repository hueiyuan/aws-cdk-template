class MSKConfig:
    instance_type = {
        'develop': 'kafka.t3.small',
        'staging': 'kafka.m5.large',
        'production': 'kafka.m5.xlarge'
    }
    
    broker_volume_size = {
        'develop': 600,
        'staging': 4000,
        'production': 12000
    }
    
    number_of_broker = {
        'develop': 2,
        'staging': 4,
        'production': 4
    }
    
    metrics_level = 'PER_TOPIC_PER_BROKER'
    kafka_version = '2.8.0'
    
