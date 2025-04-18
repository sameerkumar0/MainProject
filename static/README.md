# TaskFlow Static Files Structure

This directory contains the static files for the TaskFlow application, organized in a modular structure.

## Directory Structure

```
static/
├── css/
│   └── base.css       # Base CSS styles for the application
├── js/
│   └── base.js        # Base JavaScript functionality
└── img/               # Directory for images
```

## How to Use

### Option 1: Direct Usage with new_base.html

You can use the new base template directly by extending it in your templates:

```html
{% extends "new_base.html" %}

{% block title %}Your Page Title{% endblock %}

{% block content %}
    <!-- Your page content here -->
{% endblock %}

{% block extra_css %}
    <!-- Additional CSS for this page -->
{% endblock %}

{% block extra_js %}
    <!-- Additional JavaScript for this page -->
{% endblock %}
```

### Option 2: Gradual Migration with extended_base.html

For a gradual migration without affecting existing functionality, use the extended base template:

```html
{% extends "extended_base.html" %}

{% block title %}Your Page Title{% endblock %}

{% block page_content %}
    <!-- Your page content here -->
{% endblock %}

{% block page_css %}
    <!-- Additional CSS for this page -->
{% endblock %}

{% block page_js %}
    <!-- Additional JavaScript for this page -->
{% endblock %}
```

## Benefits

1. **Modular Structure**: CSS and JavaScript are separated into their own files
2. **Maintainability**: Easier to maintain and update styles and scripts
3. **Performance**: Static files can be cached by the browser
4. **Gradual Migration**: Can be implemented without affecting existing functionality
5. **Consistency**: Provides a consistent look and feel across the application

## Notes

- The static files are served from the `/static/` URL path
- No changes to URLs or existing functionality are required
- Both approaches (direct usage or gradual migration) can be used simultaneously
