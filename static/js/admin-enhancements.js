/**
 * LegacyAdmin - Admin Enhancement JavaScript
 * This file contains JavaScript enhancements for the admin interface.
 */

// Initialize MicroModal for modal dialogs
document.addEventListener('DOMContentLoaded', function() {
  MicroModal.init({
    onShow: modal => console.log(`${modal.id} is shown`),
    onClose: modal => console.log(`${modal.id} is hidden`),
    openTrigger: 'data-micromodal-trigger',
    closeTrigger: 'data-micromodal-close',
    disableScroll: true,
    disableFocus: false,
    awaitOpenAnimation: false,
    awaitCloseAnimation: false,
    debugMode: false
  });

  // Initialize Tippy.js for tooltips
  tippy('[data-tippy-content]', {
    arrow: true,
    animation: 'scale',
    theme: 'light-border',
    placement: 'top'
  });

  // Initialize Notyf for toast notifications
  window.notyf = new Notyf({
    duration: 3000,
    position: {
      x: 'right',
      y: 'top',
    },
    types: [
      {
        type: 'success',
        background: '#34D399',
        icon: {
          className: 'fas fa-check-circle',
          tagName: 'i'
        }
      },
      {
        type: 'error',
        background: '#F87171',
        icon: {
          className: 'fas fa-times-circle',
          tagName: 'i'
        }
      }
    ]
  });

  // HTMX Events for toast notifications
  document.body.addEventListener('htmx:afterSwap', function(evt) {
    // Only show success messages for successful form submissions (status 200 or 204)
    if (evt.detail.xhr.status === 200 || evt.detail.xhr.status === 204) {
      if (evt.detail.xhr.getResponseHeader('HX-Trigger') === 'formSubmitted') {
        window.notyf.success('Changes saved successfully!');
      }
    }
  });

  document.body.addEventListener('htmx:responseError', function(evt) {
    window.notyf.error('There was an error processing your request');
  });
  
  // Initialize SortableJS for drag-and-drop tier lists
  const tierBody = document.getElementById('tier-body');
  if (tierBody) {
    Sortable.create(tierBody, {
      handle: '.drag-handle',
      animation: 150,
      onEnd: function(evt) {
        // Update the order input fields
        const rows = tierBody.querySelectorAll('tr:not(.template)');
        rows.forEach((row, index) => {
          const orderInput = row.querySelector('input[name$="-ORDER"]');
          if (orderInput) {
            orderInput.value = index;
          }
        });
      }
    });

    // Add bulk tier functionality
    const bulkAddBtn = document.getElementById('bulk-add-btn');
    if (bulkAddBtn) {
      bulkAddBtn.addEventListener('click', function() {
        const count = parseInt(document.getElementById('bulk-add-count').value) || 1;
        const addBtn = document.querySelector('.add-row');
        
        for (let i = 0; i < count; i++) {
          if (addBtn && typeof addBtn.onclick === 'function') {
            addBtn.onclick();
          }
        }
      });
    }

    // Undo delete functionality
    document.addEventListener('click', function(e) {
      if (e.target && e.target.matches('.undo-delete')) {
        e.preventDefault();
        const row = e.target.closest('tr');
        row.classList.remove('deleted');
        const deleteCheckbox = row.querySelector('input[name$="-DELETE"]');
        if (deleteCheckbox) {
          deleteCheckbox.checked = false;
        }
      }
    });
  }

  // Bulk actions
  const bulkSelectAll = document.getElementById('bulk-select-all');
  if (bulkSelectAll) {
    bulkSelectAll.addEventListener('change', function() {
      const bulkSelects = document.querySelectorAll('.bulk-select');
      bulkSelects.forEach(checkbox => {
        checkbox.checked = bulkSelectAll.checked;
      });
    });
  }

  // Bulk delete
  const bulkDeleteBtn = document.getElementById('bulk-delete-btn');
  if (bulkDeleteBtn) {
    bulkDeleteBtn.addEventListener('click', function(e) {
      e.preventDefault();
      const selectedIds = [];
      document.querySelectorAll('.bulk-select:checked').forEach(checkbox => {
        selectedIds.push(checkbox.value);
      });
      
      if (selectedIds.length === 0) {
        window.notyf.error('Please select at least one item to delete');
        return;
      }
      
      if (confirm('Are you sure you want to delete the selected items?')) {
        const bulkForm = document.getElementById('bulk-form');
        const idsInput = document.getElementById('bulk-ids');
        idsInput.value = selectedIds.join(',');
        bulkForm.submit();
      }
    });
  }
});
