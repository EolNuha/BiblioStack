from django.shortcuts import render, get_object_or_404, redirect
from .models import Post, Comment
from taggit.models import Tag
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.template.defaultfilters import slugify
from .forms import CreatePost
from django.db.models.signals import pre_save
from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMessage
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.contrib import messages
from voting.models import Vote


def handler404(request, exception):
    context = {
        'all_posts': Post.objects.all(),
    }
    return render(request, 'datadump/post/404.html', context)


def post_list(request, tag_slug=None):
    object_list = Post.objects.all()
    tag = None
    if tag_slug:
        tag = get_object_or_404(Tag, slug=tag_slug)
        object_list = object_list.filter(tags__in=[tag])

    paginator = Paginator(object_list, 5)
    page = request.GET.get('page')
    try:
        posts = paginator.page(page)
    except PageNotAnInteger:
        posts = paginator.page(1)
    except EmptyPage:
        posts = paginator.page(paginator.num_pages)

    if request.method == 'POST':
        if 'contact_us' in request.POST:
            name = request.POST.get('first')
            last_name = request.POST.get('last')
            email = request.POST.get('email')
            phone = request.POST.get('phone')
            message = request.POST.get('message')
            html_mail = f'<h5>Phone: {phone}<br>Email: {email}</h5><p>{message}</p>'
            subject, from_email, to = name + " " + last_name, email, 'eol.nuha22@gmail.com'
            msg = EmailMessage(subject, html_mail, from_email, [to])
            msg.content_subtype = "html"
            msg.send()

    context = {
        'page': page,
        'posts': posts,
        'tag': tag,
        'all_posts': Post.objects.all(),
    }
    return render(request, 'datadump/post/list.html', context)


def post_update(request, year, month, day, post):
    post = get_object_or_404(Post, slug=post,
                             status='published',
                             publish__year=year,
                             publish__month=month,
                             publish__day=day)
    create_form = CreatePost(instance=post)
    if request.user == post.author:
        if request.method == 'POST':
            create_form = CreatePost(request.POST, instance=post)
            if create_form.is_valid():
                obj = create_form.save()
                obj.slug = slugify(obj.title)
                obj.save()
                messages.success(request, "Question Updated Successfully!")
                return redirect(f'{post.get_absolute_url()}')
            else:
                for field in create_form:
                    for error in field.errors:
                        error = error
                messages.error(request, f"{error}")
    else:
        return redirect('datadump:post_list')

    context = {
        'all_posts': Post.objects.all(),
        'post': post,
        'create_form': create_form
    }
    return render(request, 'datadump/post/update_post.html', context)


def post_detail(request, year, month, day, post):
    post_slug = post
    post = get_object_or_404(Post, slug=post,
                             status='published',
                             publish__year=year,
                             publish__month=month,
                             publish__day=day)
    comments = post.comments.filter(active=True)
    if request.method == 'POST':
        if 'contact_us' in request.POST:
            name = request.POST.get('first')
            last_name = request.POST.get('last')
            email = request.POST.get('email')
            phone = request.POST.get('phone')
            message = request.POST.get('message')
            html_mail = f'<h5>Phone: {phone}<br>Email: {email}</h5><p>{message}</p>'
            subject, from_email, to = name + " " + last_name, email, 'eol.nuha22@gmail.com'
            msg = EmailMessage(subject, html_mail, from_email, [to])
            msg.content_subtype = "html"
            msg.send()
        elif 'delete_post' in request.POST:
            Post.objects.filter(slug=post_slug, status='published', publish__year=year, publish__month=month, publish__day=day).delete()
            messages.success(request, "Question deleted successfully!")
            return redirect('datadump:post_list')
        elif 'add_post_like' in request.POST:
            up_vote = request.POST.get('up_vote')
            if up_vote == "up_vote":
                Vote.objects.record_vote(post, request.user, 0)
            else:
                Vote.objects.record_vote(post, request.user, +1)
        elif 'remove_post_like' in request.POST:
            down_vote = request.POST.get('down_vote')
            if down_vote == "down_vote":
                Vote.objects.record_vote(post, request.user, 0)
            else:
                Vote.objects.record_vote(post, request.user, -1)
        elif 'add_comment_like' in request.POST:
            comment_id = request.POST.get('comment_id')
            up_vote = request.POST.get('up_vote')
            comment = Comment.objects.get(id=comment_id)
            if up_vote == "up_vote":
                Vote.objects.record_vote(comment, request.user, 0)
            else:
                Vote.objects.record_vote(comment, request.user, +1)
        elif 'remove_comment_like' in request.POST:
            comment_id = request.POST.get('comment_id')
            comment = Comment.objects.get(id=comment_id)
            down_vote = request.POST.get('down_vote')
            if down_vote == "down_vote":
                Vote.objects.record_vote(comment, request.user, 0)
            else:
                Vote.objects.record_vote(comment, request.user, -1)
        elif 'add_comment' in request.POST:
            if request.user.is_authenticated:
                name = request.user.username
                email = request.user.email
                comment = request.POST.get('comment')
                c = Comment(post=post, name=name, email=email, body=comment)
                c.save()
                html_mail = f'<h4>{name} made a comment on your post</h4><small>Here is the comment:<br></small><strong>{comment}</strong>'
                subject, from_email, to = "Comment on post " + post.title, email, post.author.email
                msg = EmailMessage(subject, html_mail, from_email, [to])
                msg.content_subtype = "html"
                msg.send()
            else:
                name = request.POST.get('name')
                email = request.POST.get('email')
                comment = request.POST.get('comment')
                c = Comment(post=post, name=name, email=email, body=comment)
                c.save()
                html_mail = f'<h4>{name} made a comment on your post</h4><small>Here is the comment:<br></small><strong>{comment}</strong>'
                subject, from_email, to = "Comment on post " + post.title, email, post.author.email
                msg = EmailMessage(subject, html_mail, from_email, [to])
                msg.content_subtype = "html"
                msg.send()
            messages.success(request, "Comment added successfully!")
    context = {
        'post': post,
        'comments': comments,
        'all_posts': Post.objects.all(),
    }
    return render(request, 'datadump/post/detail.html', context)


@login_required
def create_post(request):
    create_form = []
    if request.method == 'POST':
        if 'contact_us' in request.POST:
            name = request.POST.get('first')
            last_name = request.POST.get('last')
            email = request.POST.get('email')
            phone = request.POST.get('phone')
            message = request.POST.get('message')
            html_mail = f'<h5>Phone: {phone}<br>Email: {email}</h5><p>{message}</p>'
            subject, from_email, to = name + " " + last_name, email, 'eol.nuha22@gmail.com'
            msg = EmailMessage(subject, html_mail, from_email, [to])
            msg.content_subtype = "html"
            msg.send()
        elif 'create_post' in request.POST:
            create_form = CreatePost(request.POST, request.FILES)
            if create_form.is_valid():
                def pre_save_post_receiver(sender, instance, *args, **kwargs):
                    instance.slug = slugify(instance.title)
                    instance.author = request.user
                    instance.status = "published"
                pre_save.connect(pre_save_post_receiver, sender=Post)
                create_form.save()
                messages.success(request, "Question posted successfully!")
                return redirect('datadump:post_list')
            else:
                for field in create_form:
                    for error in field.errors:
                        error = error
                messages.error(request, f"{error}")
    else:
        create_form = CreatePost()

    context = {
        'create_form': create_form,
        'all_posts': Post.objects.all(),
    }
    return render(request, 'datadump/post/create_post.html', context)


def search_posts(request):
    search = request.GET.get('search')
    vector = SearchVector('title', weight='A') + SearchVector('body', weight='B')
    query = SearchQuery(search)
    search_results = Post.objects.annotate(rank=SearchRank(vector, query)).filter(rank__gte=0.3).order_by('-rank')
    paginator = Paginator(search_results, 5)
    page = request.GET.get('page')
    try:
        posts = paginator.page(page)
    except PageNotAnInteger:
        posts = paginator.page(1)
    except EmptyPage:
        posts = paginator.page(paginator.num_pages)
    context = {
        'search': search,
        'page': page,
        'posts': posts,
        'search_results': search_results,
        'all_posts': Post.objects.all(),
    }
    return render(request, 'datadump/post/search_results.html', context)


def about_us(request):
    return render(request, 'datadump/common/about.html')


def faq(request):
    return render(request, 'datadump/common/faq.html')


def team(request):
    return render(request, 'datadump/common/team.html')
