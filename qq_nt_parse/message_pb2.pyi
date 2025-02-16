from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Message(_message.Message):
    __slots__ = ("messages",)
    MESSAGES_FIELD_NUMBER: _ClassVar[int]
    messages: _containers.RepeatedCompositeFieldContainer[SingleMessage]
    def __init__(self, messages: _Optional[_Iterable[_Union[SingleMessage, _Mapping]]] = ...) -> None: ...

class SingleMessage(_message.Message):
    __slots__ = ("messageId", "messageType", "senderId", "receiverId", "messageText", "fileName", "fileSize", "sendTimestampFile", "imageUrlLow", "imageUrlHigh", "imageUrlOrigin", "imageText", "senderUid", "sendTimestamp", "receiverUid", "replyMessage", "emojiId", "emojiText", "applicationMessage", "callStatusText", "callText", "feedTitle", "feedContent", "feedUrl", "feedLogoUrl", "feedPublisherUid", "feedJumpInfo", "feedPublisherId", "noticeInfo", "noticeInfo2")
    MESSAGEID_FIELD_NUMBER: _ClassVar[int]
    MESSAGETYPE_FIELD_NUMBER: _ClassVar[int]
    SENDERID_FIELD_NUMBER: _ClassVar[int]
    RECEIVERID_FIELD_NUMBER: _ClassVar[int]
    MESSAGETEXT_FIELD_NUMBER: _ClassVar[int]
    FILENAME_FIELD_NUMBER: _ClassVar[int]
    FILESIZE_FIELD_NUMBER: _ClassVar[int]
    SENDTIMESTAMPFILE_FIELD_NUMBER: _ClassVar[int]
    IMAGEURLLOW_FIELD_NUMBER: _ClassVar[int]
    IMAGEURLHIGH_FIELD_NUMBER: _ClassVar[int]
    IMAGEURLORIGIN_FIELD_NUMBER: _ClassVar[int]
    IMAGETEXT_FIELD_NUMBER: _ClassVar[int]
    SENDERUID_FIELD_NUMBER: _ClassVar[int]
    SENDTIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    RECEIVERUID_FIELD_NUMBER: _ClassVar[int]
    REPLYMESSAGE_FIELD_NUMBER: _ClassVar[int]
    EMOJIID_FIELD_NUMBER: _ClassVar[int]
    EMOJITEXT_FIELD_NUMBER: _ClassVar[int]
    APPLICATIONMESSAGE_FIELD_NUMBER: _ClassVar[int]
    CALLSTATUSTEXT_FIELD_NUMBER: _ClassVar[int]
    CALLTEXT_FIELD_NUMBER: _ClassVar[int]
    FEEDTITLE_FIELD_NUMBER: _ClassVar[int]
    FEEDCONTENT_FIELD_NUMBER: _ClassVar[int]
    FEEDURL_FIELD_NUMBER: _ClassVar[int]
    FEEDLOGOURL_FIELD_NUMBER: _ClassVar[int]
    FEEDPUBLISHERUID_FIELD_NUMBER: _ClassVar[int]
    FEEDJUMPINFO_FIELD_NUMBER: _ClassVar[int]
    FEEDPUBLISHERID_FIELD_NUMBER: _ClassVar[int]
    NOTICEINFO_FIELD_NUMBER: _ClassVar[int]
    NOTICEINFO2_FIELD_NUMBER: _ClassVar[int]
    messageId: int
    messageType: int
    senderId: str
    receiverId: str
    messageText: str
    fileName: str
    fileSize: int
    sendTimestampFile: int
    imageUrlLow: str
    imageUrlHigh: str
    imageUrlOrigin: str
    imageText: str
    senderUid: int
    sendTimestamp: int
    receiverUid: int
    replyMessage: SingleMessage
    emojiId: int
    emojiText: str
    applicationMessage: str
    callStatusText: str
    callText: str
    feedTitle: FeedMessage
    feedContent: FeedMessage
    feedUrl: str
    feedLogoUrl: str
    feedPublisherUid: int
    feedJumpInfo: str
    feedPublisherId: str
    noticeInfo: str
    noticeInfo2: str
    def __init__(self, messageId: _Optional[int] = ..., messageType: _Optional[int] = ..., senderId: _Optional[str] = ..., receiverId: _Optional[str] = ..., messageText: _Optional[str] = ..., fileName: _Optional[str] = ..., fileSize: _Optional[int] = ..., sendTimestampFile: _Optional[int] = ..., imageUrlLow: _Optional[str] = ..., imageUrlHigh: _Optional[str] = ..., imageUrlOrigin: _Optional[str] = ..., imageText: _Optional[str] = ..., senderUid: _Optional[int] = ..., sendTimestamp: _Optional[int] = ..., receiverUid: _Optional[int] = ..., replyMessage: _Optional[_Union[SingleMessage, _Mapping]] = ..., emojiId: _Optional[int] = ..., emojiText: _Optional[str] = ..., applicationMessage: _Optional[str] = ..., callStatusText: _Optional[str] = ..., callText: _Optional[str] = ..., feedTitle: _Optional[_Union[FeedMessage, _Mapping]] = ..., feedContent: _Optional[_Union[FeedMessage, _Mapping]] = ..., feedUrl: _Optional[str] = ..., feedLogoUrl: _Optional[str] = ..., feedPublisherUid: _Optional[int] = ..., feedJumpInfo: _Optional[str] = ..., feedPublisherId: _Optional[str] = ..., noticeInfo: _Optional[str] = ..., noticeInfo2: _Optional[str] = ...) -> None: ...

class FeedMessage(_message.Message):
    __slots__ = ("text",)
    TEXT_FIELD_NUMBER: _ClassVar[int]
    text: str
    def __init__(self, text: _Optional[str] = ...) -> None: ...
