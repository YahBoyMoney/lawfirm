(() => {
  const forms = document.querySelectorAll('form[data-intake-form]');
  const matterLabels = {
    'personal-injury-wrongful-death': 'Personal injury or wrongful death',
    'employment-workplace-claims': 'Employment or workplace',
    'civil-rights-government-accountability': 'Civil rights or government accountability',
    'consumer-protection-lemon-law': 'Consumer protection or Lemon Law',
    'insurance-bad-faith': 'Insurance bad faith',
    'catastrophic-injury': 'Catastrophic injury',
    'select-civil-litigation': 'Select civil litigation',
    'commercial-vehicle-accident': 'Commercial vehicle accident'
  };
  const requestedMatter = new URLSearchParams(window.location.search).get('matter');
  const setStatus = (form, message, state) => {
    const status = form.querySelector('[data-form-status]');
    if (!status) return;
    status.textContent = message;
    status.dataset.state = state;
    status.focus();
  };

  forms.forEach((form) => {
    const caseType = form.querySelector('select[name="caseType"]');
    const requestedLabel = requestedMatter ? matterLabels[requestedMatter] : '';
    if (caseType && requestedLabel && [...caseType.options].some((option) => option.value === requestedLabel)) {
      caseType.value = requestedLabel;
    }
    const phone = form.querySelector('input[type="tel"]');
    const phoneError = form.querySelector('[data-phone-error]');
    const validatePhone = () => {
      if (!phone) return true;
      const digits = phone.value.replace(/\D/g, '');
      const allowedCharacters = /^[+0-9][0-9 ().-]{5,24}$/.test(phone.value);
      const valid = !phone.value || (allowedCharacters && digits.length >= 7 && digits.length <= 15 && !/^(\d)\1+$/.test(digits));
      const message = valid ? '' : 'Enter a valid phone number with 7 to 15 digits.';
      phone.setCustomValidity(message);
      phone.setAttribute('aria-invalid', String(!valid));
      if (phoneError) phoneError.textContent = message;
      return valid;
    };
    phone?.addEventListener('input', validatePhone);
    phone?.addEventListener('blur', validatePhone);
    phone?.addEventListener('invalid', validatePhone);

    form.addEventListener('submit', (event) => {
      if (!validatePhone()) {
        event.preventDefault();
        phone.focus();
        return;
      }
      if (!form.reportValidity()) return;
      const submit = form.querySelector('[type="submit"]');
      const pageUrl = form.querySelector('[name="page_url"]');
      const referrer = form.querySelector('[name="referrer"]');
      if (pageUrl) pageUrl.value = window.location.href;
      if (referrer) referrer.value = document.referrer;
      submit.disabled = true;
      submit.setAttribute('aria-disabled', 'true');
      setStatus(form, 'Sending your request…', 'pending');
    });
  });
})();
