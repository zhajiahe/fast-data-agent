"""
文件上传 API 路由
"""

from fastapi import APIRouter, Depends, File, UploadFile, status

from app.core.deps import CurrentUser, DBSession
from app.models.base import BasePageQuery, BaseResponse, PageResponse
from app.schemas.uploaded_file import FileListQuery, FilePreviewResponse, UploadedFileResponse
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
async def get_file(file_id: int, current_user: CurrentUser, db: DBSession):
    """获取单个文件详情"""
    service = UploadedFileService(db)
    item = await service.get_file(file_id, current_user.id)
    return BaseResponse(success=True, code=200, msg="获取文件成功", data=UploadedFileResponse.model_validate(item))


@router.post("/upload", response_model=BaseResponse[UploadedFileResponse], status_code=status.HTTP_201_CREATED)
async def upload_file(
    current_user: CurrentUser,
    db: DBSession,
    file: UploadFile = File(..., description="要上传的文件"),
):
    """上传文件"""
    content = await file.read()
    service = UploadedFileService(db)
    item = await service.upload_file(
        user_id=current_user.id,
        filename=file.filename or "unknown",
        content=content,
        content_type=file.content_type,
    )
    return BaseResponse(success=True, code=201, msg="文件上传成功", data=UploadedFileResponse.model_validate(item))


@router.delete("/{file_id}", response_model=BaseResponse[None])
async def delete_file(file_id: int, current_user: CurrentUser, db: DBSession):
    """删除文件"""
    service = UploadedFileService(db)
    await service.delete_file(file_id, current_user.id)
    return BaseResponse(success=True, code=200, msg="文件删除成功", data=None)


@router.get("/{file_id}/preview", response_model=BaseResponse[FilePreviewResponse])
async def get_file_preview(
    file_id: int,
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
    file_id: int,
    current_user: CurrentUser,
    db: DBSession,
    expires: int = 3600,
):
    """获取文件下载 URL"""
    service = UploadedFileService(db)
    url = await service.get_download_url(file_id, current_user.id, expires)
    return BaseResponse(success=True, code=200, msg="获取下载链接成功", data=url)


