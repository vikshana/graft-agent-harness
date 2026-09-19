from dbos import DBOS


@DBOS.step()
async def first_step(value: str) -> str:
    return f"first:{value}"


@DBOS.step()
async def second_step(value: str) -> str:
    return f"second:{value}"


@DBOS.workflow()
async def matrix_workflow(value: str) -> str:
    return await first_step(value)
