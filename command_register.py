#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
command_register.py: 指令注册

Author: NianGui
Time  : 2022/4/23 0:23
"""
import qqbot


def cmd(command_str: str, check_param: bool = False, invalid_func=None):
    """
    指令的装饰器
    :param command_str: 指令的字符串。例如 `/菜单`
    :param check_param: 是否需要检查参数
    :param invalid_func: 当参数不符合要求时的处理函数
    :return: 装饰器
    """

    def decorator(func):
        async def wrapper(*args, **kwargs):
            if command_str != "" and command_str in args[2].content:
                qqbot.logger.info("指令处理成功: %s" % command_str)
                params = args[2].content.split(command_str)[1].strip()
                if check_param and params == "":
                    return await invalid_func(args[1], args[2])
                return await func(params, args[1], args[2])
            else:
                qqbot.logger.debug("指令未找到: %s" % command_str)
                return None

        return wrapper

    return decorator
