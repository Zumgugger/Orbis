"""
Shopping Lists Blueprint
Manage multiple shopping lists with text-based items
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from database import db, ShoppingList

bp = Blueprint('shopping', __name__, url_prefix='/shopping')

@bp.route('/')
def list():
    """Display all shopping lists"""
    lists = ShoppingList.query.order_by(ShoppingList.updated_at.desc()).all()
    return render_template('shopping/list.html', lists=lists)

@bp.route('/create', methods=['GET', 'POST'])
def create():
    """Create a new shopping list"""
    if request.method == 'POST':
        title = request.form.get('title')
        items = request.form.get('items')
        
        if not title:
            flash('Title is required!', 'error')
            return redirect(url_for('shopping.create'))
        
        shopping_list = ShoppingList(title=title, items=items)
        db.session.add(shopping_list)
        db.session.commit()
        
        flash('Shopping list created!', 'success')
        return redirect(url_for('shopping.list'))
    
    return render_template('shopping/form.html', shopping_list=None)

@bp.route('/<int:id>/edit', methods=['GET', 'POST'])
def edit(id):
    """Edit a shopping list"""
    shopping_list = ShoppingList.query.get_or_404(id)
    
    if request.method == 'POST':
        shopping_list.title = request.form.get('title')
        shopping_list.items = request.form.get('items')
        
        if not shopping_list.title:
            flash('Title is required!', 'error')
            return redirect(url_for('shopping.edit', id=id))
        
        db.session.commit()
        flash('Shopping list updated!', 'success')
        return redirect(url_for('shopping.list'))
    
    return render_template('shopping/form.html', shopping_list=shopping_list)

@bp.route('/<int:id>/delete', methods=['POST'])
def delete(id):
    """Delete a shopping list"""
    shopping_list = ShoppingList.query.get_or_404(id)
    db.session.delete(shopping_list)
    db.session.commit()
    flash('Shopping list deleted!', 'success')
    return redirect(url_for('shopping.list'))
