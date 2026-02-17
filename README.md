# 🚀 Exploria
A modern SaaS platform connecting travelers with local guides for unforgettable experiences. Built with Django and styled with Tailwind CSS, this app empowers guides to showcase their expertise and travelers to discover authentic adventures.

![Lanzaxperience Logo](https://img.shields.io/badge/Lanzaxperience-Experience%20Booking-blue?style=for-the-badge&logo=map&logoColor=white) ![Django](https://img.shields.io/badge/Django-092E20?style=for-the-badge&logo=django&logoColor=white) ![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white) ![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white) ![SQLite](https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white)

## 🌟 Features

### For Travelers
- **Browse Experiences**: Discover a wide range of authentic experiences offered by local guides, categorized by type and location.
- **Advanced Search & Filtering**: Find experiences using keywords, categories, price, duration, and location.
- **Secure Bookings**: Book experiences with real-time availability, select preferred language, transport mode, and group size (adults, children, infants).
- **Booking Management**: View and manage your bookings, track status (pending, accepted, rejected, canceled), and communicate with guides.
- **Leave Reviews**: Rate and review completed experiences to help other travelers and provide feedback to guides.
- **Personal Dashboard**: Access a personalized dashboard to view your bookings, reviews, and profile.

### For Guides
- **Create & Manage Experiences**: List your experiences with detailed descriptions, photos, pricing, duration, capacity, and tags for better discoverability.
- **Availability Management**: Set flexible availability rules including weekdays, date ranges, daily capacity limits for people and bookings, and block specific dates.
- **Booking Oversight**: Receive booking requests, accept/reject them, set pickup times and meeting points, and communicate with travelers.
- **Profile Verification**: Upload verification documents (guide license, insurance/registration) for admin approval to build trust.
- **Earnings Tracking**: Monitor bookings and potential earnings through your dashboard.
- **Public Profile**: Showcase your bio, languages spoken, contact info, and social media links.

### General Features
- **User Authentication**: Secure registration and login with role-based access (Traveler or Guide).
- **Responsive Design**: Fully responsive interface optimized for desktop, tablet, and mobile devices using Tailwind CSS.
- **Email Notifications**: Automated email notifications for booking confirmations, status updates, and responses.
- **Admin Panel**: Django admin interface for managing users, experiences, bookings, reviews, and verifications.
- **Multilingual Support**: Support for multiple languages in bookings (Spanish, English, German, French, Italian, Portuguese).
- **Image Uploads**: Upload and manage images for experiences and profiles using Pillow.
- **Moderated Reviews**: Review system with pending/published/flagged status for quality control.

## 🛠 Tech Stack

- **Backend**: Django 6.0.1 (Python web framework)
- **Frontend**: HTML5, CSS3, JavaScript, Tailwind CSS 4.1.18
- **Database**: SQLite (development), PostgreSQL (production recommended)
- **Image Processing**: Pillow 12.1.0
- **Environment Management**: django-environ 0.12.0
- **Build Tools**: Node.js, npm, PostCSS, Autoprefixer
- **Version Control**: Git
- **Deployment**: Ready for Heroku, AWS, DigitalOcean, or similar cloud platforms

## 📦 Installation

### Prerequisites
- Python 3.8+
- Node.js 14+
- Git

### Step-by-Step Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/AmeriK88/lxp-guides.git
   cd lx-guides
   ```

2. **Set up Python virtual environment**:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up Node.js dependencies for Tailwind CSS**:
   ```bash
   npm install
   ```

5. **Configure environment variables**:
   Create a `.env` file in the project root with:
   ```
   SECRET_KEY=your-secret-key-here
   DEBUG=True
   ALLOWED_HOSTS=localhost,127.0.0.1
   ```

6. **Run database migrations**:
   ```bash
   python manage.py migrate
   ```

7. **Create a superuser**:
   ```bash
   python manage.py createsuperuser
   ```

8. **Build static assets**:
   ```bash
   npm run tw:build
   ```

9. **Start the development server**:
   ```bash
   python manage.py runserver
   ```

Visit `http://127.0.0.1:8000` to see the app in action!

### Development Mode
For development with auto-reloading Tailwind CSS:
```bash
npm run tw:dev
```
This will watch for changes in `./static/src/input.css` and compile to `./static/css/output.css`.

## 🚀 Usage

### Getting Started
1. Register as either a Traveler or Guide.
2. Complete your profile setup.
3. For Guides: Upload verification documents and create your first experience.
4. For Travelers: Browse and book experiences.

### Key Workflows
- **Experience Creation**: Guides can add experiences with categories, pricing, availability rules, and media.
- **Booking Process**: Travelers select dates, group composition, and preferences; guides review and respond.
- **Availability Logic**: System prevents overbooking based on capacity limits and blocked dates.
- **Review System**: Post-booking reviews with ratings and comments, moderated by admins.

### Admin Features
Access `/admin/` with superuser credentials to manage:
- Users and profiles
- Experiences and categories
- Bookings and availability
- Reviews and moderation

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. Fork the project
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Development Guidelines
- Follow Django best practices
- Write tests for new features
- Ensure responsive design
- Use semantic commit messages

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.


---

Made by the Lxp-Guides team. Happy adventuring! 🌍✈️