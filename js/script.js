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
});
