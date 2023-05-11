import os

import qqbot
from qqbot.core.util.yaml_util import YamlUtil

import blivedm
from command_register import cmd

config = YamlUtil.read(os.path.join(os.path.dirname(__file__), "config.yml"))
T_TOKEN = qqbot.Token(config["bot"]["appid"], config["bot"]["token"])
live_clients = {}
focus_group = set()


async def _send_message(content: str, event: str, message: qqbot.Message, image: str = None):
    """
    机器人发送消息
    """
    msg_api = qqbot.AsyncMessageAPI(T_TOKEN, False)
    dms_api = qqbot.AsyncDmsAPI(T_TOKEN, False)

    send = qqbot.MessageSendRequest(content=content, msg_id=message.id, image=image)
    if event == "DIRECT_MESSAGE_CREATE":
        await dms_api.post_direct_message(message.guild_id, send)
    else:
        await msg_api.post_message(message.channel_id, send)


@cmd("/菜单")
async def ask_menu(param: str, event: str, message: qqbot.Message):
    await _send_message(get_menu(), event, message)
    return True


@cmd("/设置直播间")
async def set_live_room(param: str, event: str, message: qqbot.Message):
    if param == "":
        await _send_message("请输入直播间号", event, message)
        return True
    await run_single_client(param, event, message)
    return True


@cmd("/停止")
async def stop_client(param: str, event: str, message: qqbot.Message):
    global live_clients
    if not live_clients.__contains__(message.channel_id):
        await _send_message("没有在监听", event, message)
        return True
    if isinstance(live_clients[message.channel_id], blivedm.BLiveClient):
        client = live_clients.pop(message.channel_id)
        await client.stop_and_close()
    await _send_message("停止成功", event, message)
    return True


@cmd("/状态")
async def get_status(param: str, event: str, message: qqbot.Message):
    global live_clients
    if not live_clients.__contains__(message.channel_id):
        await _send_message("没有在监听", event, message)
        return True
    if isinstance(live_clients[message.channel_id], blivedm.BLiveClient):
        if live_clients[message.channel_id].is_running:
            await _send_message(f"监听 {live_clients[message.channel_id].room_id} 直播间中", event, message)
        else:
            await _send_message("暂停中", event, message)
    else:
        await _send_message("没有在监听", event, message)
    return True


@cmd("/设置关注用户")
async def set_focus_group(param: str, event: str, message: qqbot.Message):
    global focus_group
    if param == "":
        await _send_message("请输入监听用户", event, message)
        return True
    focus_group = set.union(focus_group, set(param.split(" ")))
    await _send_message("设置成功", event, message)
    return True


@cmd("/取消关注用户")
async def cancel_focus_group(param: str, event: str, message: qqbot.Message):
    global focus_group
    if param == "":
        await _send_message("请输入取消监听的用户", event, message)
        return True
    focus_group = focus_group - set(param.split(" "))
    await _send_message("取消成功", event, message)
    return True


@cmd("/查看关注用户")
async def get_focus_group(param: str, event: str, message: qqbot.Message):
    global focus_group
    await _send_message(",".join(focus_group), event, message)
    return True


async def run_single_client(room_id: str, event: str, message: qqbot.Message):
    global live_clients
    # 如果SSL验证失败就把ssl设为False，B站真的有过忘续证书的情况
    if live_clients.__contains__(message.channel_id):
        await _send_message("已经在监听了", event, message)
        return True
    client = blivedm.BLiveClient(room_id, ssl=True)
    handler = MyHandler(message.channel_id)
    client.add_handler(handler)

    client.start()
    await _send_message("监听成功", event, message)
    live_clients[message.channel_id] = client
    try:
        await client.join()
    finally:
        await client.stop_and_close()


class MyHandler(blivedm.BaseHandler):

    def __init__(self, channel_id: str):
        self.channel_id = channel_id

    # 演示如何添加自定义回调
    _CMD_CALLBACK_DICT = blivedm.BaseHandler._CMD_CALLBACK_DICT.copy()

    # 入场消息回调
    async def __interact_word_callback(self, client: blivedm.BLiveClient, command: dict):
        if focus_group.__contains__(str(command['data']['uid'])):
            msg_api = qqbot.AsyncMessageAPI(T_TOKEN, False)
            send = qqbot.MessageSendRequest(content=f"{command['data']['uname']} 进入了直播间")
            await msg_api.post_message(self.channel_id, send)

    _CMD_CALLBACK_DICT['INTERACT_WORD'] = __interact_word_callback  # noqa

    async def _on_heartbeat(self, client: blivedm.BLiveClient, message: blivedm.HeartbeatMessage):
        return

    async def _on_danmaku(self, client: blivedm.BLiveClient, message: blivedm.DanmakuMessage):
        if focus_group.__contains__(str(message.uid)):
            msg_api = qqbot.AsyncMessageAPI(T_TOKEN, False)
            send = qqbot.MessageSendRequest(
                content=f'[{message.medal_name} : {message.medal_level}] {message.uname}：{message.msg}')
            await msg_api.post_message(self.channel_id, send)

    async def _on_gift(self, client: blivedm.BLiveClient, message: blivedm.GiftMessage):
        if focus_group.__contains__(str(message.uid)):
            msg_api = qqbot.MessageAPI(T_TOKEN, False)
            send = qqbot.MessageSendRequest(
                content=f'{message.uname} 赠送{message.gift_name}x{message.num}'
                        f' ({message.coin_type}瓜子x{message.total_coin})')
            msg_api.post_message(self.channel_id, send)

    async def _on_buy_guard(self, client: blivedm.BLiveClient, message: blivedm.GuardBuyMessage):
        if focus_group.__contains__(str(message.uid)):
            msg_api = qqbot.AsyncMessageAPI(T_TOKEN, False)
            send = qqbot.MessageSendRequest(
                content=f'[{client.room_id}] {message.username} 购买{message.gift_name}')
            await msg_api.post_message(self.channel_id, send)

    async def _on_super_chat(self, client: blivedm.BLiveClient, message: blivedm.SuperChatMessage):
        if message.medal_name is None:
            content = f' ¥{message.price} {message.uname}: {message.message}'
        else:
            content = f' ¥{message.price} [{message.medal_name}: {message.medal_level}]  {message.uname}: {message.message} '
        msg_api = qqbot.AsyncMessageAPI(T_TOKEN, False)
        send = qqbot.MessageSendRequest(content=content)
        await msg_api.post_message(self.channel_id, send)


def get_menu():
    return """
/菜单 - 查看菜单
/设置直播间 - 设置直播间(需要停止状态)
    示例： /设置直播间 510
/停止 - 停止监听
/状态 - 查看监听状态 
/设置关注用户 - 设置关注的b站用户, 可以设置多个, 用空格分隔
    示例： /设置关注用户 544252413
/取消关注用户 - 取消关注的b站用户, 可以设置多个, 用空格分隔
    示例： /取消关注用户 544252413
/查看关注用户 - 查看已经关注的b站用户
    """


async def _message_handler(event: str, message: qqbot.Message):
    """
    定义事件回调的处理
    :param event: 事件类型
    :param message: 事件对象（如监听消息是Message对象）
    """
    qqbot.logger.info("收到消息: %s" % message.content)

    tasks = [
        ask_menu,  # /菜单
        set_live_room,  # /设置直播间
        get_status,  # /状态
        stop_client,  # /暂停
        set_focus_group,  # /设置关注组
        get_focus_group,  # /获取关注组
        cancel_focus_group  # /取消关注组
    ]
    for task in tasks:
        if await task("", event, message):
            return
    await _send_message("抱歉，没明白你的意思呢。\n" + get_menu(), event, message)


def run():
    """
    启动机器人
    """
    # @机器人后推送被动消息
    qqbot_handler = qqbot.Handler(
        qqbot.HandlerType.AT_MESSAGE_EVENT_HANDLER, _message_handler
    )
    # 私信消息
    qqbot_direct_handler = qqbot.Handler(
        qqbot.HandlerType.DIRECT_MESSAGE_EVENT_HANDLER, _message_handler
    )
    qqbot.async_listen_events(T_TOKEN, False, qqbot_handler, qqbot_direct_handler)


if __name__ == '__main__':
    run()
