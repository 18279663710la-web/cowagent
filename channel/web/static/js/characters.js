/**
 * Character management - CRUD operations for AI character companion platform
 */

// ── Data loading ──────────────────────────────────────────────────────

async function loadCharacters() {
    try {
        const resp = await fetch('/api/characters');
        const data = await resp.json();
        if (data.status !== 'success') {
            console.warn('[characters] Failed to load:', data.message);
            return;
        }
        renderCharacterList(data.characters || []);
    } catch (e) {
        console.error('[characters] Load error:', e);
    }
}

// ── Rendering ─────────────────────────────────────────────────────────

function renderCharacterList(chars) {
    const container = document.getElementById('character-list');
    if (!container) return;

    if (chars.length === 0) {
        container.innerHTML = `
            <div class="col-span-full text-center py-12 text-slate-400 dark:text-slate-500">
                <i class="fas fa-user-astronaut text-4xl mb-3 block opacity-30"></i>
                <p>暂无角色，点击"创建角色"开始</p>
            </div>`;
        return;
    }

    container.innerHTML = chars.map(c => renderCharacterCard(c)).join('');
}

function renderCharacterCard(c) {
    const exBadge = c.ex_skill
        ? '<span class="px-2 py-0.5 text-xs rounded-full bg-rose-100 dark:bg-rose-900/30 text-rose-600 dark:text-rose-400 font-medium"><i class="fas fa-heart-broken mr-1"></i>前任</span>'
        : '';
    const activeBadge = c.is_active
        ? '<span class="px-2 py-0.5 text-xs rounded-full bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400 font-medium">已激活</span>'
        : '';
    const bound = c.bound_user_id
        ? `<span class="text-xs text-slate-400 dark:text-slate-500"><i class="fas fa-link mr-1"></i>已绑定用户</span>`
        : '';

    if (c.ex_skill) {
        return `
        <div class="bg-white dark:bg-[#1A1A1A] rounded-2xl border border-slate-200 dark:border-white/10 p-5
                    hover:border-rose-300 dark:hover:border-rose-700 transition-colors duration-150">
            <div class="flex items-start justify-between mb-3">
                <div class="flex items-center gap-3">
                    <div class="w-12 h-12 rounded-xl bg-gradient-to-br from-rose-400 to-rose-600 flex items-center justify-center text-white text-lg font-bold flex-shrink-0">
                        <i class="fas fa-heart-broken"></i>
                    </div>
                    <div>
                        <h4 class="font-semibold text-slate-800 dark:text-slate-100 text-sm">${escHtml(c.name)} ${exBadge}${activeBadge}</h4>
                    </div>
                </div>
                ${bound}
            </div>
            <div class="flex items-center gap-2 pt-2 border-t border-slate-100 dark:border-white/5">
                ${c.is_active
                    ? `<button onclick="deactivateCharacter('${c.id}')"
                         class="px-3 py-1.5 text-xs rounded-lg bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-400
                                hover:bg-amber-100 dark:hover:bg-amber-900/30 transition-colors cursor-pointer">
                         <i class="fas fa-pause mr-1"></i>停用</button>`
                    : `<button onclick="activateCharacter('${c.id}')"
                         class="px-3 py-1.5 text-xs rounded-lg bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-400
                                hover:bg-emerald-100 dark:hover:bg-emerald-900/30 transition-colors cursor-pointer">
                         <i class="fas fa-play mr-1"></i>激活</button>`
                }
                <button onclick="editCharacter('${c.id}')"
                        class="px-3 py-1.5 text-xs rounded-lg bg-slate-50 dark:bg-white/5 text-slate-600 dark:text-slate-400
                               hover:bg-slate-100 dark:hover:bg-white/10 transition-colors cursor-pointer">
                    <i class="fas fa-pen mr-1"></i>编辑</button>
                <button onclick="deleteCharacter('${c.id}')"
                        class="px-3 py-1.5 text-xs rounded-lg bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400
                               hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors cursor-pointer">
                <i class="fas fa-trash mr-1"></i>删除</button>
        </div>
    </div>`;
    }

    // Regular character card
    const interests = (c.interests && c.interests.length > 0)
        ? c.interests.slice(0, 3).map(i => `<span class="px-2 py-0.5 text-xs rounded-full bg-slate-100 dark:bg-white/5 text-slate-500 dark:text-slate-400">${escHtml(i)}</span>`).join(' ')
        : '';

    return `
    <div class="bg-white dark:bg-[#1A1A1A] rounded-2xl border border-slate-200 dark:border-white/10 p-5
                hover:border-primary-300 dark:hover:border-primary-700 transition-colors duration-150">
        <div class="flex items-start justify-between mb-3">
            <div class="flex items-center gap-3">
                <div class="w-12 h-12 rounded-xl bg-gradient-to-br from-primary-400 to-primary-600 flex items-center justify-center text-white text-lg font-bold flex-shrink-0">
                    ${escHtml(c.name).charAt(0)}
                </div>
                <div>
                    <h4 class="font-semibold text-slate-800 dark:text-slate-100 text-sm">${escHtml(c.name)} ${exBadge}${activeBadge}</h4>
                    <p class="text-xs text-slate-500 dark:text-slate-400">${escHtml(c.gender)} · ${c.age}岁 · ${escHtml(c.relationship)}</p>
                </div>
            </div>
            ${bound}
        </div>
        <p class="text-sm text-slate-600 dark:text-slate-300 mb-2 line-clamp-2">${escHtml(c.personality || '暂无性格描述')}</p>
        <div class="flex flex-wrap gap-1 mb-3">${interests}</div>
        <div class="flex items-center gap-2 pt-2 border-t border-slate-100 dark:border-white/5">
            ${c.is_active
                ? `<button onclick="deactivateCharacter('${c.id}')"
                     class="px-3 py-1.5 text-xs rounded-lg bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-400
                            hover:bg-amber-100 dark:hover:bg-amber-900/30 transition-colors cursor-pointer">
                     <i class="fas fa-pause mr-1"></i>停用</button>`
                : `<button onclick="activateCharacter('${c.id}')"
                     class="px-3 py-1.5 text-xs rounded-lg bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-400
                            hover:bg-emerald-100 dark:hover:bg-emerald-900/30 transition-colors cursor-pointer">
                     <i class="fas fa-play mr-1"></i>激活</button>`
            }
            <button onclick="editCharacter('${c.id}')"
                    class="px-3 py-1.5 text-xs rounded-lg bg-slate-50 dark:bg-white/5 text-slate-600 dark:text-slate-400
                           hover:bg-slate-100 dark:hover:bg-white/10 transition-colors cursor-pointer">
                <i class="fas fa-pen mr-1"></i>编辑</button>
            <button onclick="deleteCharacter('${c.id}')"
                    class="px-3 py-1.5 text-xs rounded-lg bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400
                           hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors cursor-pointer">
                <i class="fas fa-trash mr-1"></i>删除</button>
        </div>
    </div>`;
}

// ── CRUD operations ───────────────────────────────────────────────────

function showCharacterEditor(charId) {
    const overlay = document.getElementById('character-editor-overlay');
    const title = document.getElementById('character-editor-title');
    if (!overlay) return;
    overlay.classList.remove('hidden');
    document.getElementById('char-id').value = '';

    if (charId) {
        title.textContent = '编辑角色';
        loadCharacterIntoForm(charId);
    } else {
        title.textContent = '创建角色';
        resetCharacterForm();
    }
}

function hideCharacterEditor() {
    const overlay = document.getElementById('character-editor-overlay');
    if (overlay) overlay.classList.add('hidden');
}

async function loadCharacterIntoForm(charId) {
    try {
        const resp = await fetch(`/api/characters/${charId}`);
        const data = await resp.json();
        if (data.status !== 'success') return;
        const c = data.character;
        document.getElementById('char-id').value = c.id;
        document.getElementById('char-name').value = c.name || '';
        document.getElementById('char-gender').value = c.gender || '保密';
        document.getElementById('char-age').value = c.age || 25;
        document.getElementById('char-relationship').value = c.relationship || '朋友';
        document.getElementById('char-personality').value = c.personality || '';
        document.getElementById('char-language-style').value = c.language_style || '';
        document.getElementById('char-catchphrases').value = (c.catchphrases || []).join('\n');
        document.getElementById('char-interests').value = (c.interests || []).join(',');
        document.getElementById('char-background').value = c.background || '';
    } catch (e) {
        console.error('[characters] Load detail error:', e);
    }
}

function resetCharacterForm() {
    document.getElementById('char-id').value = '';
    document.getElementById('char-name').value = '';
    document.getElementById('char-gender').value = '保密';
    document.getElementById('char-age').value = '25';
    document.getElementById('char-relationship').value = '朋友';
    document.getElementById('char-personality').value = '';
    document.getElementById('char-language-style').value = '';
    document.getElementById('char-catchphrases').value = '';
    document.getElementById('char-interests').value = '';
    document.getElementById('char-background').value = '';
}

async function saveCharacter() {
    const id = document.getElementById('char-id').value;
    const data = {
        name: document.getElementById('char-name').value.trim(),
        gender: document.getElementById('char-gender').value,
        age: parseInt(document.getElementById('char-age').value) || 25,
        relationship: document.getElementById('char-relationship').value.trim() || '朋友',
        personality: document.getElementById('char-personality').value.trim(),
        language_style: document.getElementById('char-language-style').value.trim(),
        catchphrases: document.getElementById('char-catchphrases').value.split('\n').filter(s => s.trim()),
        interests: document.getElementById('char-interests').value.split(',').map(s => s.trim()).filter(s => s),
        background: document.getElementById('char-background').value.trim(),
    };

    if (!data.name || !data.personality) {
        alert('请填写角色姓名和性格描述');
        return;
    }

    try {
        let resp;
        if (id) {
            resp = await fetch(`/api/characters/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data),
            });
        } else {
            resp = await fetch('/api/characters', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data),
            });
        }
        const result = await resp.json();
        if (result.status === 'success') {
            hideCharacterEditor();
            loadCharacters();
        } else {
            alert('保存失败: ' + (result.message || '未知错误'));
        }
    } catch (e) {
        console.error('[characters] Save error:', e);
        alert('保存失败: ' + e.message);
    }
}

async function deleteCharacter(charId) {
    if (!confirm('确定要删除这个角色吗？此操作不可撤销。')) return;
    try {
        const resp = await fetch(`/api/characters/${charId}`, { method: 'DELETE' });
        const result = await resp.json();
        if (result.status === 'success') {
            loadCharacters();
        } else {
            alert('删除失败: ' + (result.message || '未知错误'));
        }
    } catch (e) {
        console.error('[characters] Delete error:', e);
    }
}

async function activateCharacter(charId) {
    try {
        const resp = await fetch(`/api/characters/${charId}/activate`, { method: 'POST' });
        const result = await resp.json();
        if (result.status === 'success') {
            loadCharacters();
        } else {
            alert('激活失败: ' + (result.message || '未知错误'));
        }
    } catch (e) {
        console.error('[characters] Activate error:', e);
    }
}

async function deactivateCharacter(charId) {
    try {
        const resp = await fetch(`/api/characters/${charId}/deactivate`, { method: 'POST' });
        const result = await resp.json();
        if (result.status === 'success') {
            loadCharacters();
        } else {
            alert('停用失败: ' + (result.message || '未知错误'));
        }
    } catch (e) {
        console.error('[characters] Deactivate error:', e);
    }
}

// ── Utility ───────────────────────────────────────────────────────────

function escHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

// ── Init ──────────────────────────────────────────────────────────────

// Hook into view switching to auto-load characters list
// Works regardless of whether console.js has loaded yet.
window._onCharactersView = function() { loadCharacters(); };

(function waitForSwitchView() {
    if (typeof window.switchView === 'function') {
        const orig = window.switchView;
        window.switchView = function(name) {
            const result = orig.apply(this, arguments);
            if (name === 'characters') loadCharacters();
            return result;
        };
    } else {
        // console.js hasn't loaded yet, poll briefly
        var attempts = 0;
        var iv = setInterval(function() {
            attempts++;
            if (typeof window.switchView === 'function') {
                clearInterval(iv);
                const orig2 = window.switchView;
                window.switchView = function(name) {
                    const result = orig2.apply(this, arguments);
                    if (name === 'characters') loadCharacters();
                    return result;
                };
            } else if (attempts > 50) {
                clearInterval(iv);
            }
        }, 100);
    }
})();

// Backup: intercept clicks on sidebar items
document.addEventListener('click', function(e) {
    var item = e.target.closest('[data-view="characters"]');
    if (item) setTimeout(loadCharacters, 150);
});

// ── Ex (前任) Character Editor ──────────────────────────────────────────

var _exData = { fileId: '', fileName: '', parseOutput: '', persona: '', memory: '', source: 'html' };

function exSelectSource(source) {
    _exData.source = source;
    var buttons = document.querySelectorAll('.ex-source-btn');
    buttons.forEach(function(btn) {
        if (btn.getAttribute('data-source') === source) {
            btn.className = btn.className.replace(/border-slate-200 dark:border-white\/10 bg-white dark:bg-\[#1A1A1A\]/g, '');
            btn.classList.add('border-primary-400', 'bg-primary-50', 'dark:bg-primary-900/10');
        } else {
            btn.classList.remove('border-primary-400', 'bg-primary-50', 'dark:bg-primary-900/10');
            btn.classList.add('border-slate-200', 'dark:border-white/10');
            if (!btn.className.includes('bg-white')) {
                // keep existing bg
            }
        }
    });

    var textInput = document.getElementById('ex-text-input');
    var fileArea = document.getElementById('ex-file-area');
    var parseBtn = document.getElementById('ex-btn-parse');

    if (source === 'text') {
        textInput.classList.remove('hidden');
        fileArea.classList.add('hidden');
        parseBtn.disabled = false;
        _exData.fileId = '';
        _exData.fileName = '';
    } else {
        textInput.classList.add('hidden');
        fileArea.classList.remove('hidden');
        parseBtn.disabled = !_exData.fileId;
    }
}

function editCharacter(charId) {
    // Check if this is an ex-skill character — if so, show the ex editor
    fetch('/api/characters/' + charId)
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data.status === 'success' && data.character && data.character.ex_skill) {
                showExEditor(charId, data.character);
            } else {
                showCharacterEditor(charId);
            }
        })
        .catch(function() { showCharacterEditor(charId); });
}

function showExEditor(charId, charData) {
    var overlay = document.getElementById('ex-editor-overlay');
    if (!overlay) { showCharacterEditor(charId); return; }
    overlay.classList.remove('hidden');
    hideCharacterEditor();

    document.getElementById('ex-char-id').value = charId || '';
    _exData = { fileId: '', fileName: '', parseOutput: '', persona: '', memory: '' };

    if (charData) {
        document.getElementById('ex-name').value = charData.name || '';
        document.getElementById('ex-target').value = charData.bound_user_id || '';
        // Store existing persona / memory so exRestartWizard can pre-fill
        _exData._existingPersona = charData.personality || '';
        _exData._existingMemory = charData.personality || '';  // fallback — memory is in MEMORY.md
    }

    // If character already has persona data, show preview; otherwise start wizard
    if (charData && charData.personality && charData.personality.trim()) {
        _showExPreview(charData);
    } else {
        exShowStep(1);
    }
}

function _showExPreview(charData) {
    // Hide step dots, wizard steps, and any stale loading overlay
    document.getElementById('ex-steps').classList.add('hidden');
    document.getElementById('ex-loading').classList.add('hidden');
    var panels = document.querySelectorAll('.ex-step');
    panels.forEach(function(p) { p.classList.add('hidden'); });

    // Populate preview fields
    document.getElementById('ex-preview-name').value = charData.name || '';
    document.getElementById('ex-preview-persona').querySelector('pre').textContent = charData.personality || '';
    // Load memory from character workspace MEMORY.md
    var charId = charData.id || document.getElementById('ex-char-id').value;
    if (charId) {
        fetch('/api/characters/' + charId + '/memory')
            .then(function(r) { return r.json(); })
            .then(function(data) {
                var mem = (data.status === 'success' && data.memory) ? data.memory : '';
                document.getElementById('ex-preview-memory').querySelector('pre').textContent = mem;
            })
            .catch(function() {});
    }
    // Show preview
    document.getElementById('ex-step0').classList.remove('hidden');
}

function exRestartWizard() {
    // Show step dots again
    document.getElementById('ex-steps').classList.remove('hidden');
    // Hide preview
    document.getElementById('ex-step0').classList.add('hidden');
    // Pre-fill persona and memory from existing data so user can edit
    _exData.persona = _exData._existingPersona || '';
    _exData.memory = _exData._existingMemory || '';
    // Start wizard from step 1
    exShowStep(1);
}

function hideExEditor() {
    var overlay = document.getElementById('ex-editor-overlay');
    if (overlay) overlay.classList.add('hidden');
}

function exShowStep(n) {
    var steps = document.querySelectorAll('#ex-steps .step-dot');
    steps.forEach(function(dot, i) {
        if (i < n) {
            dot.className = 'step-dot w-6 h-6 rounded-full bg-primary-500 text-white flex items-center justify-center font-bold';
        } else {
            dot.className = 'step-dot w-6 h-6 rounded-full bg-slate-200 dark:bg-white/10 text-slate-500 flex items-center justify-center';
        }
    });

    var panels = document.querySelectorAll('.ex-step');
    panels.forEach(function(p) { p.classList.add('hidden'); });
    var target = document.getElementById('ex-step' + n);
    if (target) target.classList.remove('hidden');
    document.getElementById('ex-loading').classList.add('hidden');
}

function exNextStep(n) {
    if (n === 2) {
        var name = document.getElementById('ex-name').value.trim();
        var target = document.getElementById('ex-target').value.trim();
        if (!name || !target) { alert('请填写角色名和微信昵称'); return; }
    }
    exShowStep(n);
}

function exFileSelected(input) {
    if (input.files.length > 0) {
        var f = input.files[0];
        document.getElementById('ex-file-name').textContent = f.name + ' (' + (f.size / 1024).toFixed(1) + ' KB)';
        document.getElementById('ex-btn-parse').disabled = false;
    }
}

async function exParseFile() {
    var target = document.getElementById('ex-target').value.trim();
    var name = document.getElementById('ex-name').value.trim();
    var fileInput = document.getElementById('ex-file-input');
    var statusEl = document.getElementById('ex-upload-status');

    // Text source: skip upload/parse, go directly to analysis
    if (_exData.source === 'text') {
        var textContent = document.getElementById('ex-text-content').value.trim();
        if (!textContent) { alert('请粘贴关于TA的记忆内容'); return; }

        // Build a plain-text analysis summary for the LLM
        _exData.parseOutput = [
            '# 主观记忆描述',
            '来源: 口述/粘贴',
            '角色名: ' + (name || '未填写'),
            '解析昵称: ' + (target || '未填写'),
            '',
            textContent,
        ].join('\n');

        document.getElementById('ex-parse-output').querySelector('pre').textContent = _exData.parseOutput;
        exShowStep(3);
        return;
    }

    // File-based sources
    if (!fileInput.files.length) { alert('请选择文件'); return; }

    statusEl.classList.remove('hidden');
    statusEl.querySelector('span').textContent = '上传文件中...';

    var formData = new FormData();
    formData.append('chat_file', fileInput.files[0]);
    formData.append('source', _exData.source);

    try {
        var uploadResp = await fetch('/api/ex/upload', { method: 'POST', body: formData });
        var uploadData = await uploadResp.json();
        if (uploadData.status !== 'success') { alert('上传失败: ' + uploadData.message); return; }
        _exData.fileId = uploadData.file_id;

        // Parse (only for chat sources that have structured format)
        statusEl.querySelector('span').textContent = '解析中...';
        var parseResp = await fetch('/api/ex/parse', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ file_id: _exData.fileId, target: target, source: _exData.source }),
        });
        var parseData = await parseResp.json();
        statusEl.classList.add('hidden');

        if (parseData.status !== 'success') {
            // If parser is not available for this type, use raw content
            _exData.parseOutput = parseData.stdout || parseData.stderr || '文件已上传，可直接进入 LLM 分析';
        } else {
            _exData.parseOutput = parseData.analysis || parseData.stdout || parseData.stderr || '解析完成';
        }

        document.getElementById('ex-parse-output').querySelector('pre').textContent = _exData.parseOutput;
        exShowStep(3);
    } catch (e) {
        statusEl.classList.add('hidden');
        alert('操作失败: ' + e.message);
    }
}

async function exAnalyze() {
    if (!_exData.parseOutput) { alert('请先完成解析'); return; }

    exShowLoading('AI 正在分析聊天记录，提取人设和记忆...');

    try {
        var resp = await fetch('/api/ex/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                parser_output: _exData.parseOutput,
                source: _exData.source,
                basic_info: {
                    name: document.getElementById('ex-name').value.trim(),
                    target: document.getElementById('ex-target').value.trim(),
                },
            }),
        });
        var data = await resp.json();
        if (data.status !== 'success') { document.getElementById('ex-loading').classList.add('hidden'); alert('分析失败: ' + (data.message || '未知错误')); exShowStep(3); return; }

        _exData.persona = data.persona || data.raw || _exData.parseOutput;
        _exData.memory = data.memory || '';

        document.getElementById('ex-persona').value = _exData.persona;
        document.getElementById('ex-memory').value = _exData.memory;
        exShowStep(4);
    } catch (e) {
        alert('分析失败: ' + e.message);
        exShowStep(3);
    }
}

async function exCreateCharacter() {
    var name = document.getElementById('ex-name').value.trim();
    if (!name) { alert('请填写角色名'); return; }

    // Use edited values if user modified them
    var persona = document.getElementById('ex-persona').value.trim() || _exData.persona;
    var memory = document.getElementById('ex-memory').value.trim() || _exData.memory;

    exShowLoading('正在创建角色...');

    try {
        var charId = document.getElementById('ex-char-id').value;
        var body = {
            name: name,
            persona: persona,
            memory: memory,
            target: document.getElementById('ex-target').value.trim(),
            char_id: charId || '',  // empty = create new, non-empty = update existing
        };

        // Always use /api/ex/create — it handles both create and update
        // and writes MEMORY.md which the regular character PUT does not.
        var resp = await fetch('/api/ex/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        var data = await resp.json();
        if (data.status === 'success') {
            hideExEditor();
            loadCharacters();
        } else {
            document.getElementById('ex-loading').classList.add('hidden');
            exShowStep(4);
            alert('创建失败: ' + (data.message || '未知错误'));
        }
    } catch (e) {
        document.getElementById('ex-loading').classList.add('hidden');
        exShowStep(4);
        alert('创建失败: ' + e.message);
    }
}

function exShowLoading(msg) {
    var panels = document.querySelectorAll('.ex-step');
    panels.forEach(function(p) { p.classList.add('hidden'); });
    document.getElementById('ex-loading').classList.remove('hidden');
    document.getElementById('ex-loading-msg').textContent = msg;
}
