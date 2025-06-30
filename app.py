#!/usr/bin/env python3
"""
Flask Web Application for Article Summarizer Agent
Modern web interface for article summarization
"""

import os
import json
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from flask import Flask, render_template, request, jsonify, send_file, flash, redirect, url_for
from flask_cors import CORS
import uuid

# Import our modules
from main import ArticleSummarizerAgent
from config import config

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'article-summarizer-secret-key-2024')
CORS(app)

# Global variables for task management
active_tasks = {}
task_results = {}
agent = None

def initialize_agent():
    """Initialize the agent globally"""
    global agent
    try:
        agent = ArticleSummarizerAgent()
        print("✅ Article Summarizer Agent initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize agent: {str(e)}")
        agent = None

# Initialize agent on startup
initialize_agent()

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/api/summarize', methods=['POST'])
def api_summarize():
    """API endpoint for summarization"""
    if not agent:
        return jsonify({
            'success': False,
            'error': 'Agent not initialized. Please try again later.'
        }), 500
    
    try:
        data = request.get_json()
        url = data.get('url', '').strip()
        method = data.get('method', 'extractive')
        length = data.get('length', 'medium')
        
        if not url:
            return jsonify({
                'success': False,
                'error': 'URL is required'
            }), 400
        
        # Validate URL format
        if not (url.startswith('http://') or url.startswith('https://')):
            if url.startswith('www.'):
                url = 'https://' + url
            else:
                url = 'https://' + url
        
        # Update configuration
        config.summarization.method = method
        config.summarization.summary_length = length
        
        # Generate task ID
        task_id = str(uuid.uuid4())
        
        # Start background task
        active_tasks[task_id] = {
            'status': 'processing',
            'progress': 0,
            'message': 'Starting summarization...',
            'started_at': datetime.now().isoformat()
        }
        
        # Run summarization in background
        thread = threading.Thread(
            target=background_summarize,
            args=(task_id, url, agent)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': 'Summarization started'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def background_summarize(task_id: str, url: str, agent: ArticleSummarizerAgent):
    """Background task for summarization"""
    try:
        # Update task status
        active_tasks[task_id].update({
            'status': 'processing',
            'progress': 10,
            'message': 'Validating URL...'
        })
        
        time.sleep(0.5)  # Small delay for UI feedback
        
        # Update progress
        active_tasks[task_id].update({
            'progress': 20,
            'message': 'Scraping content...'
        })
        
        # Run the summarization
        result = agent.run(url)
        
        # Update task status
        if result['success']:
            active_tasks[task_id].update({
                'status': 'completed',
                'progress': 100,
                'message': 'Summarization completed successfully!'
            })
            
            # Store result
            task_results[task_id] = result
        else:
            active_tasks[task_id].update({
                'status': 'failed',
                'progress': 0,
                'message': f"Summarization failed: {result.get('error', 'Unknown error')}"
            })
            task_results[task_id] = result
            
    except Exception as e:
        active_tasks[task_id].update({
            'status': 'failed',
            'progress': 0,
            'message': f"Error: {str(e)}"
        })
        task_results[task_id] = {
            'success': False,
            'error': str(e)
        }

@app.route('/api/task/<task_id>')
def api_task_status(task_id):
    """Get task status"""
    if task_id not in active_tasks:
        return jsonify({
            'success': False,
            'error': 'Task not found'
        }), 404
    
    task_info = active_tasks[task_id].copy()
    
    # If task is completed, include result
    if task_info['status'] == 'completed' and task_id in task_results:
        result = task_results[task_id]
        task_info['result'] = {
            'summary': result.get('summary', ''),
            'statistics': result.get('statistics', {}),
            'method_used': result.get('method_used', ''),
            'execution_time': result.get('execution_time', 0),
            'files_created': result.get('files_created', {})
        }
    
    return jsonify({
        'success': True,
        'task': task_info
    })

@app.route('/api/download/<task_id>/<format>')
def api_download_file(task_id, format):
    """Download result file"""
    if task_id not in task_results:
        return jsonify({
            'success': False,
            'error': 'Task not found'
        }), 404
    
    result = task_results[task_id]
    if not result.get('success'):
        return jsonify({
            'success': False,
            'error': 'Task failed'
        }), 400
    
    files_created = result.get('files_created', {})
    if format not in files_created:
        return jsonify({
            'success': False,
            'error': 'File format not available'
        }), 404
    
    file_path = files_created[format]
    if not os.path.exists(file_path):
        return jsonify({
            'success': False,
            'error': 'File not found'
        }), 404
    
    return send_file(
        file_path,
        as_attachment=True,
        download_name=f"summary_{task_id}.{format}"
    )

@app.route('/api/status')
def api_status():
    """Get agent status"""
    if not agent:
        return jsonify({
            'success': False,
            'error': 'Agent not initialized'
        }), 500
    
    try:
        status = agent.get_status()
        return jsonify({
            'success': True,
            'status': status
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/clear-cache', methods=['POST'])
def api_clear_cache():
    """Clear cache"""
    if not agent:
        return jsonify({
            'success': False,
            'error': 'Agent not initialized'
        }), 500
    
    try:
        agent.file_manager.clear_cache()
        return jsonify({
            'success': True,
            'message': 'Cache cleared successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/history')
def history():
    """Task history page"""
    # Get completed tasks
    completed_tasks = []
    for task_id, task_info in active_tasks.items():
        if task_info['status'] in ['completed', 'failed']:
            task_data = task_info.copy()
            task_data['task_id'] = task_id
            if task_id in task_results:
                task_data['result'] = task_results[task_id]
            completed_tasks.append(task_data)
    
    # Sort by creation time (newest first)
    completed_tasks.sort(
        key=lambda x: x.get('started_at', ''),
        reverse=True
    )
    
    return render_template('history.html', tasks=completed_tasks)

@app.route('/about')
def about():
    """About page"""
    return render_template('about.html')

@app.route('/settings')
def settings():
    """Settings page"""
    return render_template('settings.html')

@app.errorhandler(404)
def not_found(error):
    """404 error handler"""
    return render_template('error.html', 
                         error_code=404, 
                         error_message="Page not found"), 404

@app.errorhandler(500)
def internal_error(error):
    """500 error handler"""
    return render_template('error.html',
                         error_code=500,
                         error_message="Internal server error"), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port) 