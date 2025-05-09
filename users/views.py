from datetime import datetime, timedelta
from django.contrib.auth.models import User
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.mail import send_mail
from django.http import Http404
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from LangDiary import settings
from calendar_integration.models import GoogleCredentials
from .forms import UserRegisterForm, UserUpdateForm, ProfileUpdateForm, PasswordResetForm, SetPasswordForm, \
    UserPreferencesForm
from .models import Goal, UserPreferences, DailyActivity    
import os 
from .forms import LanguageSelectionForm, ProficiencyLevelForm
from calendar_integration.views import get_user_credentials

def onboarding_language(request):
    if request.user.is_authenticated:
        profile = request.user.profile
        if profile.language_learning:
            return redirect('users.profile')
    
    if request.method == 'POST':
        form = LanguageSelectionForm(request.POST)
        if form.is_valid():
            request.session['onboarding_language'] = form.cleaned_data['language']
            return redirect('users.onboarding_proficiency')
    else:
        initial_data = {}
        if 'onboarding_language' in request.session:
            initial_data = {'language': request.session['onboarding_language']}
        form = LanguageSelectionForm(initial=initial_data)
    
    return render(request, 'users/onboarding/language_selection.html', {'form': form, 'step': 1, 'total_steps': 3})

def onboarding_proficiency(request):
    if 'onboarding_language' not in request.session:
        return redirect('users.onboarding_language')
    
    if request.method == 'POST':
        form = ProficiencyLevelForm(request.POST)
        if form.is_valid():
            request.session['onboarding_proficiency'] = form.cleaned_data['level']
            return redirect('users.onboarding_goals')
    else:
        initial_data = {}
        if 'onboarding_proficiency' in request.session:
            initial_data = {'level': request.session['onboarding_proficiency']}
        form = ProficiencyLevelForm(initial=initial_data)
    
    selected_language = request.session['onboarding_language']
    language_display = dict(LanguageSelectionForm.LANGUAGE_CHOICES).get(selected_language, selected_language)
    
    return render(request, 'users/onboarding/proficiency_level.html', {
        'form': form, 
        'step': 2, 
        'total_steps': 3,
        'selected_language': selected_language,
        'language_display': language_display
    })

def onboarding_goals(request):
    # Check if language and proficiency are set in session
    if 'onboarding_language' not in request.session or 'onboarding_proficiency' not in request.session:
        return redirect('users.onboarding_language')
    
    if request.method == 'POST':
        title = request.POST.get('goal_title')
        description = request.POST.get('goal_description')
        target_value_str = request.POST.get('goal_target')
        deadline = request.POST.get('goal_deadline')
        unit = request.POST.get('goal_unit')
        affects_streak = request.POST.get('affects_streak') == 'on'
        Goal.objects.create(
            user=request.user,
            title=title,
            description=description,
            target_value=float(target_value_str),
            current_value=0,  
            unit=unit,        
            deadline=deadline, 
            affects_streak=affects_streak
        )
        profile = request.user.profile
        profile.language_learning = request.session['onboarding_language']
        profile.language_level = request.session['onboarding_proficiency']
        print(request.session['onboarding_language'])
        print(request.session['onboarding_proficiency'])
        print(profile.language_learning)
        profile.save()
        return redirect('users.onboarding_complete')
    return render(request, 'users/onboarding/learning_goals.html')

def onboarding_complete(request):
    profile = request.user.profile
    print(f"the profile is {profile}")
    print(f"but the language is {profile.language_learning}")
    
    
    return render(request, 'users/onboarding/onboarding_complete.html', {
        'profile': profile,
        'language_display': profile.language_learning,
        'level_display': profile.language_level,
    })

def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)

        if request.POST.get('email') and User.objects.filter(email=request.POST.get('email')).exists():
            form.add_error('email', 'Email already registered.')
        elif form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}! Please complete your profile.')

            # Log the user in automatically after registration
            user = authenticate(username=form.cleaned_data['username'],
                                password=form.cleaned_data['password1'])
            login(request, user)

            # Redirect to profile page
            return redirect('users.onboarding_language')
    else:
        form = UserRegisterForm()
    
    context = {
        'form': form,
        'template_data': {
            'title': 'Register - LangDiary'
        }
    }
    return render(request, 'users/register.html', context)

@login_required
@login_required
def profile(request):
    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)
        
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, 'Your account has been updated!')
            return redirect('users.profile')
    else:
        # Ensure we have fresh data by explicitly refreshing from DB
        request.user.refresh_from_db()
        
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=request.user.profile)
    
    # Get the user's goals with a fresh query
    user_goals = Goal.objects.filter(user=request.user)
    
    # Get a fresh profile object
    profile = request.user.profile

    authenticated = False
    if get_user_credentials(request.user):
        authenticated = True
    profile_data = {
        'profile': profile,
        'language': profile.language_learning,
        "skill": profile.language_level,
        "authenticated": authenticated
    }
    
    context = {
        'u_form': u_form,
        'p_form': p_form,
        'user_goals': user_goals,
        "profile_data": profile_data,
        "profile": profile,
    }
    return render(request, 'users/profile.html', context)

@login_required
def create_goal(request):
    if request.method == 'POST':
        title = request.POST.get('goal_title')
        description = request.POST.get('goal_description')
        target_value = int(request.POST.get('goal_target'))
        unit = request.POST.get('goal_unit')
        # Handle the deadline field properly
        deadline_str = request.POST.get('goal_deadline')
        if deadline_str and deadline_str.strip():
            # If a deadline was provided, use it
            deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date()
        else:
            # If no deadline was provided, use the default (3 days from now)
            deadline = datetime.now().date() + timedelta(days=3)
            
        affects_streak = request.POST.get('affects_streak') == 'on'
        
        Goal.objects.create(
            user=request.user,
            title=title,
            description=description,
            target_value=target_value,
            current_value=0,  
            unit=unit,        
            deadline=deadline,
            affects_streak=affects_streak
        )
        
        messages.success(request, 'Goal created successfully!')
        return redirect('users.profile')
    
    return redirect('users.profile')

@login_required
def delete_profile_picture(request):
    """
    View to handle deleting the user's profile picture and replacing it with the default
    """
    if request.method == 'POST':
        profile = request.user.profile
        
        # Check if user has a custom profile picture (not the default)
        if profile.profile_picture and not profile.profile_picture.url.endswith('default.jpg'):
            # Get the file path
            if os.path.exists(profile.profile_picture.path):
                # Delete the physical file
                os.remove(profile.profile_picture.path)
            
            # Reset to default
            profile.profile_picture = 'profile_pics/default.jpg'
            profile.save()
            
            messages.success(request, 'Your profile picture has been removed.')
        else:
            messages.info(request, 'No custom profile picture to delete.')
            
    return redirect('users.profile')


@login_required
def edit_goal(request, goal_id):
    """View to handle editing an existing goal"""
    try:
        # Get the goal and verify it belongs to the current user
        goal = Goal.objects.get(id=goal_id, user=request.user)
    except Goal.DoesNotExist:
        messages.error(request, "Goal not found or you don't have permission to edit it.")
        return redirect('users.profile')
    
    if request.method == 'POST':
        # Update goal with form data
        goal.title = request.POST.get('goal_title')
        goal.description = request.POST.get('goal_description')
        goal.target_value = float(request.POST.get('goal_target'))
        goal.current_value = float(request.POST.get('goal_current', 0))
        goal.unit = request.POST.get('goal_unit')
        goal.deadline = request.POST.get('goal_deadline') or None
        goal.affects_streak = request.POST.get('affects_streak') == 'on'
        
        goal.save()
        messages.success(request, 'Goal updated successfully!')
        return redirect('users.profile')
    
    # For GET requests, render the form
    return render(request, 'users/edit_goal.html', {'goal': goal})

@login_required
def delete_goal(request, goal_id):
    """View to handle deleting a goal"""
    try:
        # Get the goal and verify it belongs to the current user
        goal = Goal.objects.get(id=goal_id, user=request.user)
    except Goal.DoesNotExist:
        messages.error(request, "Goal not found or you don't have permission to delete it.")
        return redirect('users.profile')
    
    if request.method == 'POST':
        # Delete the goal
        goal.delete()
        messages.success(request, 'Goal deleted successfully!')
    
    return redirect('users.profile')

# Update the existing update_goal_progress view
@login_required
def update_goal_progress(request, goal_id):
    """View to handle updating the progress of a goal"""
    try:
        goal = Goal.objects.get(id=goal_id, user=request.user)
    except Goal.DoesNotExist:
        messages.error(request, "Goal not found.")
        return redirect('users.profile')
    
    streak_updated = False

    if request.method == 'POST':
        # Get current value before update
        old_value = goal.current_value
        
        # Update the current value
        new_value = float(request.POST.get('current_value', 0))
        goal.current_value = new_value
        goal.save()
        
        # Update stats in the profile
        profile = request.user.profile
        
        # Update exercises_completed if this is a lesson goal
        if goal.unit.lower() == 'exercises':
            profile.exercises_completed += new_value
        
        elif goal.unit.lower() == 'flashcards':
            # Add the flashcards completed to flashcards_completed
            profile.flashcards_completed += new_value
        
        elif goal.unit.lower() == 'videos':
            # Add the videos completed to videos_completed
            profile.videos_completed += new_value
        
        elif goal.unit.lower() == 'langlocale_activities':
            # Add the langlocale_activities completed to langlocale_activities_completed
            profile.langlocale_activities_completed += new_value
        
        # Save the profile changes
        profile.save()

        # Check if the goal was completed with this update
        if goal.is_completed and old_value < goal.target_value:
            # If this goal affects streak, update the streak
            if goal.affects_streak:
                # Get old streak value
                old_streak = request.user.profile.learning_streak
                
                # Update streak
                DailyActivity.mark_goal_completed(request.user)
                
                # Get new streak value
                request.user.refresh_from_db()
                new_streak = request.user.profile.learning_streak
                
                # Check if streak was incremented
                streak_updated = True
                
                messages.success(request, 'Goal completed! Your streak has been updated!')
            else:
                messages.success(request, 'Goal completed!')
        else:
            messages.success(request, 'Progress updated!')
    if streak_updated:
        return redirect(f"{reverse('users.profile')}?streak_celebration=true")
    else:
        return redirect('users.profile')

    # Force a refresh of the page (to ensure all data is updated)
    return redirect('users.profile')
# Add to views.py
@login_required
def complete_daily_goal(request):
    """
    Mark the user's daily goal as completed and update their streak
    """
    # You could determine which goal is the daily goal based on your app's logic
    # For example, it could be goals with unit='days' or a specific goal type
    
    daily_goals = Goal.objects.filter(user=request.user, unit='days')
    daily_goal_completed = any(goal.check_daily_goal_completion() for goal in daily_goals)
    
    if daily_goal_completed:
        # Mark the daily goal as completed and update streak
        DailyActivity.mark_goal_completed(request.user)
        messages.success(request, 'Daily goal completed! Your streak has been updated.')
    else:
        messages.info(request, 'Complete your daily goal to maintain your streak!')
    
    return redirect('users.profile')

def reset_password_request(request):
    if request.method == 'POST':
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            try:
                user = User.objects.get(email=form.cleaned_data['email'])
                token = PasswordResetTokenGenerator().make_token(user=user)
                uid = urlsafe_base64_encode(str(user.id).encode())
                url = reverse('new_password', kwargs={'uid': uid, 'token': token})

                send_mail(
                    subject='Password Reset Request LangDiary',
                    message=f'Click the link below to reset your password http://127.0.0.1:8000{url}',
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=[user.email],
                    fail_silently=False,
                )
            except Exception as e:
                print("error while sending email")
                print(e)
            return render(request, 'users/reset_password_request_done.html')

    else:
        form = PasswordResetForm()

    context = {
        'form': form,
        'template_data': {
            'title': 'Reset Password - LangDiary'
        }
    }
    return render(request, 'users/reset_password_request.html', context)


def new_password(request, uid, token):

    try:
        user = User.objects.get(id=urlsafe_base64_decode(uid))
        token_generator = PasswordResetTokenGenerator()
        if not token_generator.check_token(user, token):
            raise Http404("Invalid or expired token.")

    except (User.DoesNotExist, ValueError, TypeError):
        raise Http404("Invalid or expired token.")

    if request.method == 'POST':
        print("bcd")
        form = SetPasswordForm(user=user, data=request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Your password has been successfully reset.")
            return redirect('users.login')
    else:
        form = SetPasswordForm(user=user)

    return render(request, 'users/new_password.html', {'form': form})

@login_required
def set_preferences(request):
    # Check if user already has preferences
    try:
        preferences = UserPreferences.objects.get(user=request.user)
        # Pre-fill form with existing data
        form = UserPreferencesForm(instance=preferences)
    except UserPreferences.DoesNotExist:
        # Create new form if no preferences exist
        form = UserPreferencesForm()
        preferences = None

    if request.method == 'POST':
        if preferences:
            # Update existing preferences
            form = UserPreferencesForm(request.POST, instance=preferences)
        else:
            # Create new preferences
            form = UserPreferencesForm(request.POST)

        if form.is_valid():
            preferences = form.save(commit=False)
            preferences.user = request.user
            preferences.save()

            messages.success(request, "Your preferences have been saved successfully!")
            return redirect('users.profile')  # Redirect to profile page after saving

    return render(request, 'users/preferences.html', {'form': form})