def prepare_list_to_tuple(list_nums:list|set|tuple) -> str:
    if not list_nums:
        return ''
    if isinstance(list_nums,(set,tuple)):
        list_nums = list(list_nums)
    if isinstance(list_nums[0], float) or isinstance(list_nums[0], int):
        tmp_list = [str(_) for _ in list_nums]
        return ','.join(tmp_list)
    tmp_list = [f'{_!r}' for _ in list_nums]
    if len(tmp_list) == 1:
        return tmp_list[0]
    return ','.join(tmp_list)
