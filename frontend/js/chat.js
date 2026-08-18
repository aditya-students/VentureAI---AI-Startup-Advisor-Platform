/* ==========================================================================
   VentureAI — chat.js
   Real-Time Mentor-Founder Chat Frontend logic.
   Supports REST API fallback + WebSockets, file attachments, read receipts,
   typing indicators, unread counts, and mobile responsiveness.
   ========================================================================== */

(function () {
  'use strict';

  let currentUser = null;
  let conversations = [];
  let activeConversationId = null;
  let activeConversation = null;
  let activeMessages = [];
  let ws = null;
  let typingTimer = null;
  let selectedFile = null;
  let nextBeforeId = null;
  let hasMoreMessages = false;

  /* ---------------------------------------------------------
     DOM Elements
  --------------------------------------------------------- */
  const chatApp = document.getElementById('chat-app');
  const convListContainer = document.getElementById('conversation-list');
  const searchInput = document.getElementById('chat-search');
  const totalUnreadBadge = document.getElementById('total-unread-badge');

  const emptyState = document.getElementById('chat-empty-state');
  const activeContainer = document.getElementById('chat-active-container');
  const backBtn = document.getElementById('chat-back-btn');

  const headerAvatar = document.getElementById('chat-header-avatar');
  const headerOnlineDot = document.getElementById('chat-header-online-dot');
  const headerName = document.getElementById('chat-header-name');
  const headerRole = document.getElementById('chat-header-role');
  const headerWorkspace = document.getElementById('chat-header-workspace');
  const headerStatusPill = document.getElementById('chat-header-status-pill');

  const chatThread = document.getElementById('chat-thread');
  const messagesContainer = document.getElementById('messages-container');
  const loadOlderBtn = document.getElementById('chat-load-older-btn');
  const typingIndicatorBox = document.getElementById('typing-indicator-box');
  const typingUserName = document.getElementById('typing-user-name');

  const inputForm = document.getElementById('chat-input-form');
  const textarea = document.getElementById('chat-textarea');
  const attachBtn = document.getElementById('chat-attach-btn');
  const fileInput = document.getElementById('chat-file-input');
  const filePreviewBox = document.getElementById('file-preview-box');
  const filePreviewName = document.getElementById('file-preview-name');
  const filePreviewCancel = document.getElementById('file-preview-cancel');
  const sendBtn = document.getElementById('chat-send-btn');
  const disabledBox = document.getElementById('chat-disabled-box');

  /* ---------------------------------------------------------
     Helpers & Utilities
  --------------------------------------------------------- */
  function getInitials(name) {
    if (!name || !name.trim()) return '?';
    const parts = name.trim().split(/\s+/);
    if (parts.length === 1) return parts[0].charAt(0).toUpperCase();
    return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase();
  }

  function formatTime(isoStr) {
    if (!isoStr) return '';
    const d = new Date(isoStr);
    const now = new Date();
    const isToday = d.toDateString() === now.toDateString();
    if (isToday) {
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
    return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
  }

  function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  }

  function getOtherParticipant(conv) {
    if (!currentUser || !conv) return { name: 'User', role: 'Participant' };
    if (currentUser.id === conv.founder_id) {
      return {
        name: conv.mentor ? conv.mentor.name : 'Mentor',
        role: 'Mentor',
        profile: conv.mentor,
      };
    } else {
      return {
        name: conv.founder ? conv.founder.name : 'Founder',
        role: 'Founder',
        profile: conv.founder,
      };
    }
  }

  /* ---------------------------------------------------------
     API Calls
  --------------------------------------------------------- */
  async function fetchConversations() {
    try {
      const res = await apiRequest('/mentor/conversations');
      conversations = res.conversations || [];
      renderConversationList();
    } catch (err) {
      convListContainer.innerHTML = `<div style="padding:1.5rem; color:#ef4444; font-size:0.85rem;">Failed loading conversations: ${err.message}</div>`;
    }
  }

  async function loadMessages(convId, beforeId = null) {
    let path = `/mentor/conversations/${convId}/messages?limit=40`;
    if (beforeId) path += `&before_id=${beforeId}`;
    return await apiRequest(path);
  }

  /* ---------------------------------------------------------
     Render Conversation List
  --------------------------------------------------------- */
  function renderConversationList() {
    const query = searchInput ? searchInput.value.toLowerCase().trim() : '';
    const filtered = conversations.filter(conv => {
      const other = getOtherParticipant(conv);
      const wsName = conv.workspace ? conv.workspace.name.toLowerCase() : '';
      return other.name.toLowerCase().includes(query) || wsName.includes(query);
    });

    let totalUnread = 0;
    conversations.forEach(c => { totalUnread += (c.unread_count || 0); });

    if (totalUnreadBadge) {
      if (totalUnread > 0) {
        totalUnreadBadge.textContent = totalUnread > 99 ? '99+' : totalUnread;
        totalUnreadBadge.style.display = 'inline-flex';
      } else {
        totalUnreadBadge.style.display = 'none';
      }
    }

    if (!filtered.length) {
      convListContainer.innerHTML = `
        <div style="padding:2rem 1rem; text-align:center; color:var(--chat-muted); font-size:0.875rem;">
          ${query ? 'No matching conversations found.' : 'No mentorship conversations yet.'}
        </div>
      `;
      return;
    }

    convListContainer.innerHTML = filtered.map(conv => {
      const other = getOtherParticipant(conv);
      const isActive = conv.id === activeConversationId;
      const initials = getInitials(other.name);
      const timeStr = formatTime(conv.last_message_at || conv.created_at);
      const unread = conv.unread_count || 0;
      const isMentorRole = other.role === 'Mentor';

      let lastMsgText = 'No messages yet';
      if (conv.last_message) {
        lastMsgText = conv.last_message.content;
      }

      return `
        <div class="conversation-item ${isActive ? 'active' : ''}" data-conv-id="${conv.id}">
          <div class="avatar-wrap">
            <div class="chat-avatar">${initials}</div>
            <span class="online-dot" data-user-dot="${other.profile ? (other.profile.user_id || other.profile.id) : ''}"></span>
          </div>
          <div class="conversation-info">
            <div class="conversation-info__top">
              <span class="conversation-name">${other.name}</span>
              <span class="conversation-time">${timeStr}</span>
            </div>
            <div class="conversation-meta">
              <span class="role-tag ${isMentorRole ? 'role-tag--mentor' : ''}">${other.role}</span>
              ${conv.workspace ? `<span class="workspace-tag">● ${conv.workspace.name}</span>` : ''}
            </div>
            <div class="conversation-preview-row">
              <span class="conversation-preview ${unread > 0 ? 'unread' : ''}">${lastMsgText}</span>
              ${unread > 0 ? `<span class="unread-badge">${unread}</span>` : ''}
            </div>
          </div>
        </div>
      `;
    }).join('');

    convListContainer.querySelectorAll('.conversation-item').forEach(el => {
      el.addEventListener('click', () => {
        const id = parseInt(el.dataset.convId, 10);
        selectConversation(id);
      });
    });
  }

  /* ---------------------------------------------------------
     Select Conversation & Open Chat Viewport
  --------------------------------------------------------- */
  async function selectConversation(convId) {
    activeConversationId = convId;
    renderConversationList();

    chatApp.classList.add('show-viewport');
    emptyState.style.display = 'none';
    activeContainer.style.display = 'flex';

    messagesContainer.innerHTML = '<div style="text-align:center; color:var(--chat-muted); padding:2rem;">Loading messages…</div>';

    try {
      activeConversation = await apiRequest(`/mentor/conversations/${convId}`);
      updateHeaderInfo();

      const res = await loadMessages(convId);
      activeMessages = res.messages || [];
      hasMoreMessages = res.has_more;
      nextBeforeId = res.next_before_id;

      renderMessageThread();
      scrollToBottom();

      // Connect WebSocket
      setupWebSocket(convId);

      // Mark messages read
      if (activeConversation.unread_count > 0) {
        await apiRequest(`/mentor/conversations/${convId}/read`, { method: 'POST' });
        activeConversation.unread_count = 0;
        fetchConversations();
      }

    } catch (err) {
      messagesContainer.innerHTML = `<div style="padding:2rem; color:#ef4444; text-align:center;">Failed loading chat: ${err.message}</div>`;
    }
  }

  function updateHeaderInfo() {
    if (!activeConversation) return;
    const other = getOtherParticipant(activeConversation);
    headerAvatar.textContent = getInitials(other.name);
    headerName.textContent = other.name;
    headerRole.textContent = other.role;
    headerRole.className = `role-tag ${other.role === 'Mentor' ? 'role-tag--mentor' : ''}`;

    if (activeConversation.workspace) {
      headerWorkspace.textContent = `Startup: ${activeConversation.workspace.name}`;
      headerWorkspace.style.display = 'inline';
    } else {
      headerWorkspace.style.display = 'none';
    }

    const convStatus = (activeConversation.status || 'active').toLowerCase();
    headerStatusPill.textContent = convStatus === 'active' ? 'Active Mentorship' : 'Read Only';
    headerStatusPill.className = `chat-status-pill ${convStatus}`;

    // Enable / Disable input based on status
    if (convStatus === 'read_only' || convStatus === 'archived') {
      inputForm.style.display = 'none';
      disabledBox.style.display = 'block';
    } else {
      inputForm.style.display = 'flex';
      disabledBox.style.display = 'none';
    }
  }

  /* ---------------------------------------------------------
     Render Message Thread
  --------------------------------------------------------- */
  function renderMessageThread() {
    loadOlderBtn.style.display = hasMoreMessages ? 'block' : 'none';

    if (!activeMessages.length) {
      messagesContainer.innerHTML = `
        <div style="text-align:center; padding:3rem 1rem; color:var(--chat-muted);">
          No messages in this conversation yet. Send a greeting to start chatting!
        </div>
      `;
      return;
    }

    messagesContainer.innerHTML = activeMessages.map(msg => {
      const isOutgoing = msg.sender_id === currentUser.id;
      const isSystem = msg.message_type === 'system';
      const timeStr = formatTime(msg.created_at);

      if (isSystem) {
        return `<div class="system-message">ℹ️ ${msg.content}</div>`;
      }

      let attachmentsHtml = '';
      if (msg.attachments && msg.attachments.length) {
        attachmentsHtml = msg.attachments.map(att => `
          <div class="attachment-card">
            <span class="attachment-icon">📄</span>
            <div class="attachment-info">
              <div class="attachment-name">${att.file_name}</div>
              <div class="attachment-size">${formatFileSize(att.file_size)}</div>
            </div>
            <a href="${API_BASE_URL}${att.download_url}" target="_blank" class="attachment-download-link" download>Download</a>
          </div>
        `).join('');
      }

      let checkmarks = '';
      if (isOutgoing) {
        if (msg.is_read) {
          checkmarks = '<span class="read-checkmarks is-read">✓✓</span>';
        } else if (msg.delivered_at) {
          checkmarks = '<span class="read-checkmarks">✓✓</span>';
        } else {
          checkmarks = '<span class="read-checkmarks">✓</span>';
        }
      }

      return `
        <div class="message-row ${isOutgoing ? 'message-row--outgoing' : 'message-row--incoming'}">
          <div class="message-bubble">
            ${msg.content}
            ${attachmentsHtml}
          </div>
          <div class="message-meta">
            <span>${timeStr}</span>
            ${checkmarks}
          </div>
        </div>
      `;
    }).join('');
  }

  function scrollToBottom() {
    setTimeout(() => {
      chatThread.scrollTop = chatThread.scrollHeight;
    }, 50);
  }

  /* ---------------------------------------------------------
     WebSocket Real-time Handling
  --------------------------------------------------------- */
  function setupWebSocket(convId) {
    if (ws) {
      ws.close();
      ws = null;
    }

    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsHost = window.location.hostname || '127.0.0.1';
    const wsUrl = `${wsProtocol}//${wsHost}:8000/mentor/chat/${convId}`;

    try {
      ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        if (headerOnlineDot) headerOnlineDot.classList.add('is-online');
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          handleWebSocketEvent(data);
        } catch (_) {}
      };

      ws.onclose = () => {
        if (headerOnlineDot) headerOnlineDot.classList.remove('is-online');
      };

      ws.onerror = () => {
        if (headerOnlineDot) headerOnlineDot.classList.remove('is-online');
      };
    } catch (_) {}
  }

  function handleWebSocketEvent(data) {
    if (!data || !data.type) return;

    if (data.type === 'new_message' && data.conversation_id === activeConversationId) {
      const exists = activeMessages.some(m => m.id === data.message.id);
      if (!exists) {
        activeMessages.push(data.message);
        renderMessageThread();
        scrollToBottom();
      }

      // If message is from recipient, mark read immediately
      if (data.message.sender_id !== currentUser.id) {
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'mark_read' }));
        }
      }
      fetchConversations();
    }
    else if (data.type === 'messages_read' && data.conversation_id === activeConversationId) {
      activeMessages.forEach(m => { if (m.sender_id === currentUser.id) m.is_read = true; });
      renderMessageThread();
    }
    else if (data.type === 'typing_start' && data.conversation_id === activeConversationId) {
      if (data.user_id !== currentUser.id) {
        typingUserName.textContent = data.user_name || 'Participant';
        typingIndicatorBox.style.display = 'flex';
        scrollToBottom();
      }
    }
    else if (data.type === 'typing_stop' && data.conversation_id === activeConversationId) {
      typingIndicatorBox.style.display = 'none';
    }
    else if (data.type === 'presence_update') {
      const dot = document.querySelector(`[data-user-dot="${data.user_id}"]`);
      if (dot) {
        if (data.status === 'online') dot.classList.add('is-online');
        else dot.classList.remove('is-online');
      }
    }
  }

  /* ---------------------------------------------------------
     Sending Messages & Attachments
  --------------------------------------------------------- */
  async function handleSendMessage(e) {
    e.preventDefault();
    if (!activeConversationId) return;

    const content = textarea.value.trim();
    if (!content && !selectedFile) return;

    sendBtn.disabled = true;

    try {
      let msgRes;
      if (selectedFile) {
        // Upload attachment
        const formData = new FormData();
        formData.append('file', selectedFile);

        const res = await fetch(`${API_BASE_URL}/mentor/conversations/${activeConversationId}/attachments`, {
          method: 'POST',
          credentials: 'include',
          body: formData,
        });

        if (!res.ok) {
          const errData = await res.json();
          throw new Error(errData.detail || 'Failed uploading attachment.');
        }

        msgRes = await res.json();
        clearFileSelection();
      } else {
        // Send text message
        msgRes = await apiRequest(`/mentor/conversations/${activeConversationId}/messages`, {
          method: 'POST',
          body: { content, message_type: 'text' },
        });
      }

      if (msgRes && msgRes.id) {
        const exists = activeMessages.some(m => m.id === msgRes.id);
        if (!exists) {
          activeMessages.push(msgRes);
          renderMessageThread();
          scrollToBottom();
        }
      }

      textarea.value = '';
      textarea.style.height = 'auto';
      fetchConversations();

      // Stop typing
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'typing_stop' }));
      }
    } catch (err) {
      alert(`Error sending message: ${err.message}`);
    } finally {
      sendBtn.disabled = false;
    }
  }

  function handleTypingInput() {
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';

    if (ws && ws.readyState === WebSocket.OPEN && activeConversationId) {
      ws.send(JSON.stringify({ type: 'typing_start' }));
      clearTimeout(typingTimer);
      typingTimer = setTimeout(() => {
        ws.send(JSON.stringify({ type: 'typing_stop' }));
      }, 1500);
    }
  }

  /* ---------------------------------------------------------
     Attachment Selection
  --------------------------------------------------------- */
  function clearFileSelection() {
    selectedFile = null;
    fileInput.value = '';
    filePreviewBox.style.display = 'none';
  }

  if (attachBtn && fileInput) {
    attachBtn.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', () => {
      if (fileInput.files && fileInput.files[0]) {
        selectedFile = fileInput.files[0];
        filePreviewName.textContent = `${selectedFile.name} (${formatFileSize(selectedFile.size)})`;
        filePreviewBox.style.display = 'flex';
      }
    });
  }

  if (filePreviewCancel) {
    filePreviewCancel.addEventListener('click', clearFileSelection);
  }

  /* ---------------------------------------------------------
     Init & Event Listeners
  --------------------------------------------------------- */
  document.addEventListener('DOMContentLoaded', async () => {
    // Wait for route guard verification
    await new Promise((resolve) => {
      let attempts = 0;
      const check = () => {
        if (document.body.classList.contains('route-verified')) resolve();
        else if (attempts > 60) resolve();
        else {
          attempts++;
          setTimeout(check, 50);
        }
      };
      check();
    });

    currentUser = await getCurrentUser();
    if (!currentUser) return;

    await fetchConversations();

    // Check URL parameters for direct conversation navigation
    const urlParams = new URLSearchParams(window.location.search);
    const paramConvId = urlParams.get('conversation_id');
    const paramMentorId = urlParams.get('mentor_id');
    const paramConnectionId = urlParams.get('connection_id');

    if (paramConvId) {
      selectConversation(parseInt(paramConvId, 10));
    } else if (paramMentorId || paramConnectionId) {
      try {
        const payload = {};
        if (paramMentorId) payload.mentor_id = parseInt(paramMentorId, 10);
        if (paramConnectionId) payload.connection_id = parseInt(paramConnectionId, 10);

        const conv = await apiRequest('/mentor/conversations', {
          method: 'POST',
          body: payload,
        });
        await fetchConversations();
        selectConversation(conv.id);
      } catch (err) {
        alert(`Cannot open chat: ${err.message}`);
      }
    }

    // UI Event listeners
    if (searchInput) searchInput.addEventListener('input', renderConversationList);
    if (inputForm) inputForm.addEventListener('submit', handleSendMessage);
    if (textarea) {
      textarea.addEventListener('input', handleTypingInput);
      textarea.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          inputForm.dispatchEvent(new Event('submit'));
        }
      });
    }

    if (backBtn) {
      backBtn.addEventListener('click', () => {
        chatApp.classList.remove('show-viewport');
      });
    }

    if (loadOlderBtn) {
      loadOlderBtn.addEventListener('click', async () => {
        if (!activeConversationId || !nextBeforeId) return;
        loadOlderBtn.disabled = true;
        try {
          const res = await loadMessages(activeConversationId, nextBeforeId);
          hasMoreMessages = res.has_more;
          nextBeforeId = res.next_before_id;
          const newOlderMessages = (res.messages || []).filter(nm => !activeMessages.some(m => m.id === nm.id));
          activeMessages = [...newOlderMessages, ...activeMessages];
          renderMessageThread();
        } catch (_) {
        } finally {
          loadOlderBtn.disabled = false;
        }
      });
    }
  });

})();
