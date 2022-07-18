from django import forms

from .models import Post, Comment


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ('text', 'group', 'image')
        labels = {'text': 'Текст сюда', 'group': 'Любую или никакую группу'}
        help_texts = {'text': 'Всё что угодно', 'group': 'Из предложеных :)'}


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('text',)
        labels = {'text': 'Сюда текст'}
        help_texts = {'text': 'Что думаешь'}
