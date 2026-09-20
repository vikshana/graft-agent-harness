from dbos import DBOS


def workflow_helper(value: str) -> str:
    return f"helper-v1:{value}"


@DBOS.workflow()
async def matrix_workflow(value: str) -> str:
    return workflow_helper(value)
