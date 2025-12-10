"""
分析会话 API 路由
"""

from typing import Any

from fastapi import APIRouter, Depends, UploadFile, status
from fastapi.responses import StreamingResponse

from app.core.deps import CurrentUser, DBSession
from app.models.base import BasePageQuery, BaseResponse, PageResponse
from app.schemas.data_source import DataSourceResponse
from app.schemas.session import (
    AnalysisSessionCreate,
    AnalysisSessionDetail,
    AnalysisSessionListQuery,
    AnalysisSessionResponse,
    AnalysisSessionUpdate,
)
from app.services.session import AnalysisSessionService
from app.utils.tools import get_sandbox_client

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("", response_model=BaseResponse[PageResponse[AnalysisSessionResponse]])
async def get_sessions(
    db: DBSession,
    current_user: CurrentUser,
    page_query: BasePageQuery = Depends(),
    query_params: AnalysisSessionListQuery = Depends(),
):
    """获取会话列表（分页）"""
    service = AnalysisSessionService(db)
    items, total = await service.get_sessions(
        user_id=current_user.id,
        query_params=query_params,
        page_num=page_query.page_num,
        page_size=page_query.page_size,
    )
    data_list = [AnalysisSessionResponse.model_validate(item) for item in items]
    return BaseResponse[PageResponse[AnalysisSessionResponse]](
        success=True,
        code=200,
        msg="获取会话列表成功",
        data=PageResponse[AnalysisSessionResponse](
            page_num=page_query.page_num, page_size=page_query.page_size, total=total, items=data_list
        ),
    )


@router.get("/{session_id}", response_model=BaseResponse[AnalysisSessionDetail])
async def get_session(
    session_id: int,
    current_user: CurrentUser,
    db: DBSession,
):
    """获取单个会话详情（包含数据源信息）"""
    service = AnalysisSessionService(db)
    session, data_source = await service.get_session_with_data_source(session_id, current_user.id)

    # 构建响应
    response = AnalysisSessionDetail(
        id=session.id,
        user_id=session.user_id,
        name=session.name,
        description=session.description,
        data_source_id=session.data_source_id,
        config=session.config,
        status=session.status,
        message_count=session.message_count,
        create_time=session.create_time,
        update_time=session.update_time,
        data_source=DataSourceResponse.model_validate(data_source) if data_source else None,
    )

    return BaseResponse[AnalysisSessionDetail](success=True, code=200, msg="获取会话成功", data=response)


@router.post("", response_model=BaseResponse[AnalysisSessionResponse], status_code=status.HTTP_201_CREATED)
async def create_session(
    data: AnalysisSessionCreate,
    current_user: CurrentUser,
    db: DBSession,
):
    """创建会话"""
    service = AnalysisSessionService(db)
    item = await service.create_session(current_user.id, data)
    return BaseResponse(success=True, code=201, msg="创建会话成功", data=AnalysisSessionResponse.model_validate(item))


@router.put("/{session_id}", response_model=BaseResponse[AnalysisSessionResponse])
async def update_session(
    session_id: int,
    data: AnalysisSessionUpdate,
    current_user: CurrentUser,
    db: DBSession,
):
    """更新会话"""
    service = AnalysisSessionService(db)
    item = await service.update_session(session_id, current_user.id, data)
    return BaseResponse(success=True, code=200, msg="更新会话成功", data=AnalysisSessionResponse.model_validate(item))


@router.delete("/{session_id}", response_model=BaseResponse[None])
async def delete_session(
    session_id: int,
    current_user: CurrentUser,
    db: DBSession,
):
    """删除会话"""
    service = AnalysisSessionService(db)
    await service.delete_session(session_id, current_user.id)
    return BaseResponse(success=True, code=200, msg="删除会话成功", data=None)


@router.post("/{session_id}/archive", response_model=BaseResponse[AnalysisSessionResponse])
async def archive_session(
    session_id: int,
    current_user: CurrentUser,
    db: DBSession,
):
    """归档会话"""
    service = AnalysisSessionService(db)
    item = await service.archive_session(session_id, current_user.id)
    return BaseResponse(success=True, code=200, msg="会话已归档", data=AnalysisSessionResponse.model_validate(item))


# ==================== 会话文件管理 ====================


@router.post("/{session_id}/files/upload", response_model=BaseResponse[dict[str, Any]])
async def upload_session_file(
    session_id: int,
    file: UploadFile,
    current_user: CurrentUser,
    db: DBSession,
):
    """
    上传文件到会话目录

    用于上传临时数据文件供 AI 分析使用。
    文件会保存到沙盒的会话目录中。
    """
    # 验证会话权限
    service = AnalysisSessionService(db)
    await service.get_session(session_id, current_user.id)

    # 调用 sandbox API 上传文件
    client = get_sandbox_client()
    content = await file.read()

    response = await client.post(
        "/upload",
        params={"user_id": current_user.id, "thread_id": session_id},
        files={"file": (file.filename, content, file.content_type or "application/octet-stream")},
    )
    result = response.json()

    if not result.get("success"):
        return BaseResponse(success=False, code=500, msg=result.get("message", "上传失败"), data=None)

    return BaseResponse(
        success=True,
        code=200,
        msg="文件上传成功",
        data={
            "filename": file.filename,
            "path": result.get("path"),
        },
    )


@router.get("/{session_id}/files", response_model=BaseResponse[dict[str, Any]])
async def list_session_files(session_id: int, current_user: CurrentUser, db: DBSession):
    """
    列出会话文件

    返回会话目录中的所有文件，包括：
    - 用户上传的数据文件
    - SQL 查询结果的 parquet 缓存
    - 生成的图表文件
    - 其他分析过程中产生的文件
    """
    # 验证会话权限
    service = AnalysisSessionService(db)
    await service.get_session(session_id, current_user.id)

    # 调用 sandbox API
    client = get_sandbox_client()
    response = await client.get(
        "/files",
        params={"user_id": current_user.id, "thread_id": session_id},
    )
    result = response.json()

    return BaseResponse(
        success=True,
        code=200,
        msg="获取文件列表成功",
        data={"files": result.get("files", []), "count": result.get("count", 0)},
    )


@router.get("/{session_id}/files/{filename:path}")
async def download_session_file(
    session_id: int,
    filename: str,
    current_user: CurrentUser,
    db: DBSession,
):
    """
    下载会话文件

    Args:
        session_id: 会话 ID
        filename: 文件名（相对于会话目录的路径）
    """
    # 验证会话权限
    service = AnalysisSessionService(db)
    await service.get_session(session_id, current_user.id)

    # 调用 sandbox API 流式下载
    client = get_sandbox_client()
    response = await client.get(
        f"/download/{filename}",
        params={"user_id": current_user.id, "thread_id": session_id},
    )

    if response.status_code == 404:
        return BaseResponse(success=False, code=404, msg="文件不存在", data=None)

    if response.status_code != 200:
        return BaseResponse(success=False, code=response.status_code, msg="下载失败", data=None)

    # 流式返回文件内容
    return StreamingResponse(
        iter([response.content]),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
