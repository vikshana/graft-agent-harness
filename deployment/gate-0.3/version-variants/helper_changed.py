from dbos import DBOS


def workflow_helper(value: str) -> str:
    return f"helper-v2:{value}"


@DBOS.step()
async def first_step(value: str) -> str:
    return f"first:{value}"


@DBOS.step()
async def second_step(value: str) -> str:
    return f"second:{value}"


@DBOS.workflow()
async def matrix_workflow(value: str) -> str:
    first = await first_step(value)
    return await second_step(workflow_helper(first))
