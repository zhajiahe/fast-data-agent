"""
文件上传 API 路由
"""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, File, UploadFile, status

from app.core.deps import CurrentUser, DBSession
from app.models.base import BasePageQuery, BaseResponse, PageResponse
from app.schemas.uploaded_file import (
    FileListQuery,
    FilePreviewResponse,
    UploadedFileResponse,
    UploadedFileWithRawDataResponse,
)
from app.services.uploaded_file import UploadedFileService

router = APIRouter(prefix="/files", tags=["files"])


@router.get("", response_model=BaseResponse[PageResponse[UploadedFileResponse]])
async def get_files(
    db: DBSession,
    current_user: CurrentUser,
    page_query: BasePageQuery = Depends(),
    query_params: FileListQuery = Depends(),
):
    """获取文件列表（分页）"""
    service = UploadedFileService(db)
    items, total = await service.get_files(
        user_id=current_user.id,
        query_params=query_params,
        page_num=page_query.page_num,
        page_size=page_query.page_size,
    )
    data_list = [UploadedFileResponse.model_validate(item) for item in items]
    return BaseResponse(
        success=True,
        code=200,
        msg="获取文件列表成功",
        data=PageResponse(page_num=page_query.page_num, page_size=page_query.page_size, total=total, items=data_list),
    )


@router.get("/{file_id}", response_model=BaseResponse[UploadedFileResponse])
async def get_file(file_id: uuid.UUID, current_user: CurrentUser, db: DBSession):
    """获取单个文件详情"""
    service = UploadedFileService(db)
    item = await service.get_file(file_id, current_user.id)
    return BaseResponse(success=True, code=200, msg="获取文件成功", data=UploadedFileResponse.model_validate(item))


@router.post(
    "/upload", response_model=BaseResponse[UploadedFileWithRawDataResponse], status_code=status.HTTP_201_CREATED
)
async def upload_file(
    current_user: CurrentUser,
    db: DBSession,
    file: UploadFile = File(..., description="要上传的文件"),
    auto_create_raw_data: bool = True,
):
    """
    上传文件

    自动创建对应的 RawData（可通过 auto_create_raw_data 参数控制）
    """
    content = await file.read()
    service = UploadedFileService(db)
    uploaded_file, raw_data = await service.upload_file(
        user_id=current_user.id,
        filename=file.filename or "unknown",
        content=content,
        content_type=file.content_type,
        auto_create_raw_data=auto_create_raw_data,
    )

    # 构建响应（手动构建避免触发关联关系懒加载）
    response_dict: dict[str, Any] = {
        "id": uploaded_file.id,
        "user_id": uploaded_file.user_id,
        "original_name": uploaded_file.original_name,
        "object_key": uploaded_file.object_key,
        "file_type": uploaded_file.file_type,
        "file_size": uploaded_file.file_size,
        "mime_type": uploaded_file.mime_type,
        "row_count": uploaded_file.row_count,
        "column_count": uploaded_file.column_count,
        "columns_info": uploaded_file.columns_info,
        "status": uploaded_file.status,
        "error_message": uploaded_file.error_message,
        "create_time": uploaded_file.create_time,
        "update_time": uploaded_file.update_time,
        "auto_raw_data": raw_data,
    }
    response_data = UploadedFileWithRawDataResponse.model_validate(response_dict)

    return BaseResponse(success=True, code=201, msg="文件上传成功", data=response_data)


@router.delete("/{file_id}", response_model=BaseResponse[None])
async def delete_file(file_id: uuid.UUID, current_user: CurrentUser, db: DBSession):
    """删除文件"""
    service = UploadedFileService(db)
    await service.delete_file(file_id, current_user.id)
    return BaseResponse(success=True, code=200, msg="文件删除成功", data=None)


@router.get("/{file_id}/preview", response_model=BaseResponse[FilePreviewResponse])
async def get_file_preview(
    file_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
    rows: int = 100,
):
    """获取文件预览"""
    service = UploadedFileService(db)
    preview = await service.get_preview(file_id, current_user.id, rows)
    return BaseResponse(success=True, code=200, msg="获取预览成功", data=preview)


@router.get("/{file_id}/download-url", response_model=BaseResponse[str])
async def get_download_url(
    file_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
    expires: int = 3600,
):
    """获取文件下载 URL"""
    service = UploadedFileService(db)
    url = await service.get_download_url(file_id, current_user.id, expires)
    return BaseResponse(success=True, code=200, msg="获取下载链接成功", data=url)
