// Luhn algorithm for South African ID validation
function luhnCheck(id) {
    if (!/^\d{13}$/.test(id)) return false;
    let sum = 0;
    let alternate = false;
    for (let i = id.length - 1; i >= 0; i--) {
        let n = parseInt(id[i], 10);
        if (alternate) {
            n *= 2;
            if (n > 9) n -= 9;
        }
        sum += n;
        alternate = !alternate;
    }
    return (sum % 10 === 0);
}

document.addEventListener('DOMContentLoaded', function() {
    const benIdInput = document.querySelector('input[name="ben-id_number"], input[name="id_number"]');
    if (!benIdInput) return;
    const errorMsgId = 'ben-id-luhn-error';
    let errorElem = document.getElementById(errorMsgId);
    if (!errorElem) {
        errorElem = document.createElement('p');
        errorElem.id = errorMsgId;
        errorElem.style.color = 'red';
        errorElem.style.fontSize = '0.9em';
        benIdInput.parentNode.appendChild(errorElem);
    }
    benIdInput.addEventListener('input', function() {
        const val = benIdInput.value.trim();
        if (val.length === 13 && !luhnCheck(val)) {
            errorElem.textContent = 'Invalid South African ID number (Luhn check failed)';
        } else {
            errorElem.textContent = '';
        }
    });
});
