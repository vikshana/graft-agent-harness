from dbos import DBOS


@DBOS.step()
async def first_step(value: str) -> str:
    return f"first:{value}"


@DBOS.step()
async def second_step(value: str) -> str:
    return f"second:{value}"


@DBOS.step()
async def third_step(value: str) -> str:
    return f"third:{value}"


@DBOS.workflow()
async def matrix_workflow(value: str) -> str:
    first = await first_step(value)
    second = await second_step(first)
    return await third_step(second)
