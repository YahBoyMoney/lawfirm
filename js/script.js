// Initialize AOS
document.addEventListener('DOMContentLoaded', function() {
  AOS.init({
    duration: 800,
    once: true,
    offset: 100
  });
  
  // Preloader
  setTimeout(function() {
    document.querySelector('.preloader').style.opacity = '0';
    setTimeout(function() {
      document.querySelector('.preloader').style.display = 'none';
    }, 500);
  }, 1000);
  
  // Navbar Scroll Effect
  const navbar = document.querySelector('.navbar');
  window.addEventListener('scroll', function() {
    if (window.scrollY > 100) {
      navbar.classList.add('nav-scrolled');
    } else {
      navbar.classList.remove('nav-scrolled');
    }
  });
  
  // Back to Top Button
  const backToTopButton = document.querySelector('.back-to-top');
  window.addEventListener('scroll', function() {
    if (window.scrollY > 300) {
      backToTopButton.classList.add('active');
    } else {
      backToTopButton.classList.remove('active');
    }
  });
  
  backToTopButton.addEventListener('click', function() {
    window.scrollTo({
      top: 0,
      behavior: 'smooth'
    });
  });
  
  // Dark Mode Toggle
  const darkModeToggle = document.querySelector('.dark-mode-toggle');
  const body = document.body;
  
  darkModeToggle.addEventListener('click', function() {
    body.classList.toggle('dark-mode');
    
    if (body.classList.contains('dark-mode')) {
      darkModeToggle.innerHTML = '<i class="fas fa-sun"></i>';
    } else {
      darkModeToggle.innerHTML = '<i class="fas fa-moon"></i>';
    }
  });
  
  // Count Up Animation
  const countUpElements = document.querySelectorAll('.count-up');
  
  const isInViewport = function(element) {
    const rect = element.getBoundingClientRect();
    return (
      rect.top >= 0 &&
      rect.left >= 0 &&
      rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
      rect.right <= (window.innerWidth || document.documentElement.clientWidth)
    );
  };
  
  const countUp = function(element) {
    const target = parseFloat(element.getAttribute('data-count'));
    const duration = 2000;
    const start = Date.now();
    const isDecimal = target % 1 !== 0;
    
    const formatNumber = function(num) {
      if (isDecimal) {
        return '$' + num.toFixed(1);
      } else {
        return '$' + num.toLocaleString();
      }
    };
    
    const updateCount = function() {
      const now = Date.now();
      const progress = Math.min((now - start) / duration, 1);
      const easeProgress = progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress);
      const currentCount = target * easeProgress;
      
      element.textContent = formatNumber(currentCount);
      
      if (progress < 1) {
        requestAnimationFrame(updateCount);
      }
    };
    
    updateCount();
  };
  
  const handleScroll = function() {
    countUpElements.forEach(function(element) {
      if (isInViewport(element) && !element.classList.contains('counted')) {
        element.classList.add('counted');
        countUp(element);
      }
    });
  };
  
  window.addEventListener('scroll', handleScroll);
  handleScroll();
  
  // Chat Widget
  const chatButton = document.querySelector('.chat-button');
  
  chatButton.addEventListener('click', function() {
    alert('Live chat feature would open here. This is just a demo.');
  });
  
  // Form Validation
  const contactForm = document.getElementById('contact-form');
  const footerForm = document.querySelector('#footer-form form');
  
  if (contactForm) {
    contactForm.addEventListener('submit', function(e) {
      e.preventDefault();
      alert('Form submitted! In a real website, this would be connected to your CRM or email system.');
    });
  }
  
  if (footerForm) {
    footerForm.addEventListener('submit', function(e) {
      e.preventDefault();
      alert('Form submitted! In a real website, this would be connected to your CRM or email system.');
    });
  }

  // Claim Analyzer Form
  const claimAnalyzerForm = document.getElementById('claim-analyzer-form');
  if (claimAnalyzerForm) {
    const steps = Array.from(claimAnalyzerForm.querySelectorAll('.form-step'));
    const nextBtns = claimAnalyzerForm.querySelectorAll('.next-step');
    const prevBtns = claimAnalyzerForm.querySelectorAll('.prev-step');
    const injurySeveritySlider = document.getElementById('injurySeverity');
    const injurySeverityValue = document.getElementById('injurySeverityValue');
    const resultsDiv = document.getElementById('claim-results');
    const estimatedValueEl = document.getElementById('estimated-value');
    const resultsSummaryEl = document.getElementById('results-summary');

    let currentStep = 0;

    const showStep = (stepIndex) => {
      steps.forEach((step, index) => {
        step.style.display = index === stepIndex ? 'block' : 'none';
      });
    };

    nextBtns.forEach(button => {
      button.addEventListener('click', () => {
        const currentStepFields = steps[currentStep].querySelectorAll('[required]');
        let isValid = true;
        currentStepFields.forEach(field => {
          if (!field.value.trim() || (field.type === 'checkbox' && !field.checked)) {
            if(field.tagName.toLowerCase() !== 'select' || field.value === '') {
              isValid = false;
            }
          }
        });

        if (isValid) {
          currentStep++;
          if (currentStep >= steps.length) {
            currentStep = steps.length - 1;
          }
          showStep(currentStep);
        } else {
          alert('Please fill out all required fields.');
        }
      });
    });

    prevBtns.forEach(button => {
      button.addEventListener('click', () => {
        currentStep--;
        if (currentStep < 0) {
          currentStep = 0;
        }
        showStep(currentStep);
      });
    });

    if (injurySeveritySlider) {
        injurySeveritySlider.addEventListener('input', (e) => {
            if(injurySeverityValue) {
                injurySeverityValue.textContent = e.target.value;
            }
        });
    }

    claimAnalyzerForm.addEventListener('submit', (e) => {
      e.preventDefault();

      const accidentType = document.getElementById('accidentType').value;
      const injurySeverity = parseInt(document.getElementById('injurySeverity').value, 10);
      const medicalBills = parseFloat(document.getElementById('medicalBills').value) || 0;
      const lostWages = parseFloat(document.getElementById('lostWages').value) || 0;
      const propertyDamage = parseFloat(document.getElementById('propertyDamage').value) || 0;
      const name = document.getElementById('analyzerName').value;
      const phone = document.getElementById('analyzerPhone').value;
      const email = document.getElementById('analyzerEmail').value;

      const multiplier = 1.5 + (injurySeverity - 1) * (3.5 / 9);

      const economicDamages = medicalBills + lostWages;
      const nonEconomicDamages = economicDamages * multiplier;
      const totalEstimate = nonEconomicDamages + propertyDamage;

      const formatter = new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
      });

      const lowEstimate = totalEstimate * 0.8;
      const highEstimate = totalEstimate * 1.2;

      estimatedValueEl.textContent = `${formatter.format(lowEstimate)} - ${formatter.format(highEstimate)}`;

      resultsSummaryEl.innerHTML = `
        <li><strong>Name:</strong> ${name}</li>
        <li><strong>Phone:</strong> ${phone}</li>
        <li><strong>Email:</strong> ${email}</li>
        <li><strong>Accident Type:</strong> ${accidentType}</li>
        <li><strong>Injury Severity:</strong> ${injurySeverity}/10</li>
        <li><strong>Medical Bills:</strong> ${formatter.format(medicalBills)}</li>
        <li><strong>Lost Wages:</strong> ${formatter.format(lostWages)}</li>
        <li><strong>Property Damage:</strong> ${formatter.format(propertyDamage)}</li>
      `;

      claimAnalyzerForm.style.display = 'none';
      resultsDiv.style.display = 'block';

      console.log({
          name, phone, email, accidentType, injurySeverity, medicalBills, lostWages, propertyDamage, estimatedCaseValue: totalEstimate
      });
    });

    showStep(currentStep);
  }
});
