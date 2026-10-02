const switches = ['banModeSwitch', 'showBannedSwitch', 'showAllSwitch'];

switches.forEach(id => {
    const currentSwitch = document.getElementById(id);
    if (!currentSwitch) return;

    currentSwitch.addEventListener('change', function () {
        if (this.checked) {
            switches.forEach(otherId => {
                if (otherId !== id) {
                    const otherSwitch = document.getElementById(otherId);
                    if (otherSwitch && otherSwitch.checked) {
                        otherSwitch.checked = false;
                        // Kích hoạt sự kiện change thủ công để các logic xóa layer của switch đó được chạy
                        otherSwitch.dispatchEvent(new Event('change'));
                    }
                }
            });
        }
    });
});

const findPathBtn = document.getElementById('findPathBtn');
if (findPathBtn) {
    findPathBtn.addEventListener('click', function () {
        switches.forEach(id => {
            const sw = document.getElementById(id);
            if (sw && sw.checked) {
                sw.checked = false;
                sw.dispatchEvent(new Event('change'));
            }
        });
    });
}