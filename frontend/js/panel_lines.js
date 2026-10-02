// Tab Lines: danh sách tuyến, click để làm nổi bật tuyến trên bản đồ
const linesPanel = {
    el: document.getElementById('panel-lines'),

    init() {
        this.render();
        this.el.addEventListener('click', (ev) => {
            const it = ev.target.closest('[data-line]');
            if (it) this.focus(it.dataset.line);
            else if (ev.target.closest('[data-act="clear"]')) this.focus(null);
        });
        store.on('lineFocus', () => this.render());
        store.on('active', () => this.render());
    },

    focus(code) {
        net.focusLine(net.state.lineFocus === code ? null : code, { fit: code !== null });
    },

    render() {
        const sel = net.state.lineFocus;
        const items = store.sortedLines(store.lines.keys()).map((code) => {
            const l = store.lines.get(code);
            const banned = l.edgeIds.filter((id) => !store.edges.get(id).active).length;
            const bannedSt = [...l.nodeIds].filter((id) => !store.nodes.get(id).active).length;
            return `<div class="card item ${sel === code ? 'selected' : ''}" style="--c:#${l.color}" data-line="${code}" tabindex="0">
                <span class="line-swatch" style="--c:#${l.color};--t:${textOn('#' + l.color)}">${esc(code)}</span>
                <div class="item-main">
                    <div class="item-top"><span class="item-title">${esc(l.name)} Line</span></div>
                    <div class="item-sub">
                        <span>${l.nodeIds.size} stations</span><span>${l.edgeIds.length} segments</span>
                        ${banned || bannedSt ? `<span class="bad">${bannedSt + banned} banned</span>` : ''}
                    </div>
                </div>
            </div>`;
        }).join('');

        this.el.innerHTML = `<div class="filters" style="position:static">
                <div class="count" style="margin:0 0 8px">${store.lines.size} lines${sel ? ` · highlighting <b>${esc(store.lines.get(sel).name)}</b> · <button class="link" data-act="clear">Clear</button>` : ' · click a line to highlight it'}</div>
            </div>
            <div class="list">${items}</div>`;
    },
};
