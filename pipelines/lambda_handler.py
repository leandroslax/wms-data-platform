from pipelines.extraction.oracle_connector import OracleConnector


def handler(event, context):
    connector = OracleConnector()
    return {
        "statusCode": 200,
        "body": {
            "message": "WMS extraction scaffold ready",
            "source": connector.healthcheck(),
        },
    }
