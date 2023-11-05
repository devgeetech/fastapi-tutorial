from fastapi import status, HTTPException, Depends, APIRouter
from sqlalchemy.orm import Session
from sqlalchemy import func
from .. import models, oauth2, schemas
from ..database import get_db
from typing import List, Optional

router = APIRouter(prefix="/posts", tags=["Posts"])


@router.get("/", response_model=List[schemas.PostOut])
async def get_posts(
    db: Session = Depends(get_db),
    current_user: schemas.UserOut = Depends(oauth2.get_current_user),
    limit: Optional[int] = 10,
    skip: Optional[int] = 0,
    search: Optional[str] = "",
):
    # cursor.execute("""SELECT * FROM posts""")
    # db_posts = cursor.fetchall()

    posts_with_votes = (
        db.query(models.Post, func.count(models.Vote.post_id).label("votes"))
        .join(models.Vote, models.Vote.post_id == models.Post.id, isouter=True)
        .group_by(models.Post.id)
        .filter(models.Post.title.contains(search))
        .limit(limit)
        .offset(skip)
        .all()
    )

    result = []
    for post, votes in posts_with_votes:
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")
        post_data = schemas.PostOut(**post.__dict__, votes=votes, owner=current_user)
        result.append(post_data)

    return result


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.Post)
async def create_posts(
    post: schemas.PostCreate,
    db: Session = Depends(get_db),
    current_user: schemas.UserOut = Depends(oauth2.get_current_user),
):
    # cursor.execute(
    #     """ INSERT INTO posts (title, content, published) VALUES (%s, %s, %s) RETURNING * """,
    #     (post.title, post.content, post.published),
    # )
    # new_post = cursor.fetchone()
    # conn.commit()
    new_post = models.Post(owner_id=current_user.id, **post.dict())
    db.add(new_post)
    db.commit()
    db.refresh(new_post)
    return new_post


@router.get("/{id}", response_model=schemas.PostOut)
async def get_post(
    id: int,
    db: Session = Depends(get_db),
    current_user: schemas.UserOut = Depends(oauth2.get_current_user),
):
    # cursor.execute("""SELECT * FROM posts WHERE id = %s """, (str(id),))
    # post = cursor.fetchone()
    # if not post:
    #     raise HTTPException(
    #         status_code=status.HTTP_404_NOT_FOUND,
    #         detail=f"post with id: {id} does not exist",
    #     )
    # return {"post_detail": post}
    post = (
        db.query(models.Post, func.count(models.Vote.post_id).label("votes"))
        .join(models.Vote, models.Vote.post_id == models.Post.id, isouter=True)
        .group_by(models.Post.id)
        .filter(models.Post.id == id)
        .first()
    )
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"post with id: {id} does not exist",
        )
    return post


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    id: int,
    db: Session = Depends(get_db),
    current_user: schemas.UserOut = Depends(oauth2.get_current_user),
):
    # cursor.execute("""DELETE FROM posts WHERE id = %s RETURNING * """, (str(id),))
    # deleted_post = cursor.fetchone()
    # conn.commit()

    # if deleted_post == None:
    #     raise HTTPException(
    #         status_code=status.HTTP_404_NOT_FOUND,
    #         detail=f"post with id: {id} does not exist",
    #     )

    # return Response(status_code=status.HTTP_204_NO_CONTENT)
    post_query = db.query(models.Post).filter(models.Post.id == id)
    post = post_query.first()
    if post == None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"post with id: {id} does not exist",
        )

    if post.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"you are not authorized to delete this post",
        )

    post_query.delete(synchronize_session=False)
    db.commit()


@router.put("/{id}", response_model=schemas.Post)
async def update_post(
    id: int,
    updated_post: schemas.PostUpdate,
    db: Session = Depends(get_db),
    current_user: schemas.UserOut = Depends(oauth2.get_current_user),
):
    # cursor.execute(
    #     """ UPDATE posts SET title = %s, content = %s, published = %s WHERE id = %s RETURNING * """,
    #     (post.title, post.content, post.published, str(id)),
    # )
    # updated_post = cursor.fetchone()
    # conn.commit()
    # if updated_post == None:
    #     raise HTTPException(
    #         status_code=status.HTTP_404_NOT_FOUND,
    #         detail=f"post with id: {id} does not exist",
    #     )
    # return {"data": updated_post}

    post_query = db.query(models.Post).filter(models.Post.id == id)
    post = post_query.first()

    if post == None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"post with id: {id} does not exist",
        )

    if post.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"you are not authorized to update this post",
        )

    post_query.update(updated_post.dict(), synchronize_session=False)
    db.commit()
    return post_query.first()
