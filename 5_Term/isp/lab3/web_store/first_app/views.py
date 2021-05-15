from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.urls import reverse
from django import views

from .models import *
from .forms import UserForm, ProfileForm 
from cart.forms import CartAddProductForm
from recommendations.models import StatisticsItem

# for EMAIL confirmation.
from django.core.mail import EmailMessage
from .tokens import my_token_generator
from django.template.loader import render_to_string
from django.contrib.sites.shortcuts import get_current_site
from django.utils.encoding import force_bytes, force_text, DjangoUnicodeDecodeError
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode

def get_products_page(request):
    # Обрабатываю параметры строки запроса с именем "category".
    choosen_category = request.GET.get("category", "")    

    products = None
    if (choosen_category != ""):
        products = Product.objects.all().filter(category__slug=choosen_category)
    else:
        products = Product.objects.all()
    return render(request, "first_app/products.html", {'products': products, 'category':choosen_category})    

def get_specific_product(request, slug):

    product = Product.objects.get(slug=slug)  

    # Collect statistics.
    StatisticsItem.add_click(user=request.user, product=product)

    cart_product_form = CartAddProductForm()
    context = {'product': product,
               'cart_product_form': cart_product_form}
    return render(request, 'first_app/specific_product.html', context)

def get_about_us(request):
    return render(request, "first_app/about_us.html", {})

def get_categories(request):

    categories = Category.objects.all()
    return render(request, "first_app/categories.html", {'categories': categories})

def loginPage(request):

    if (request.method == 'POST'):
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        try:
            user = User.objects.get(username=username)
            if user.profile.email_is_verifyed:
                user = authenticate(request, username=username, password=password)
                if user is not None:
                    login(request, user)
                    return redirect('categories_url')
                else:
                    messages.info(request, 'Username or password is not correct')
                    context = {} 
                    return render(request, 'first_app/login.html', context)   
            else:
                messages.error(request, 'Email was not verifyed yet !')
                return redirect('login_url')
        except Exception as e:
            messages.error(request, 'no user with such username')
            return redirect('login_url')
    else:
        context = {} 
        return render(request, 'first_app/login.html', context)   

def logout_user(request):
    user = request.user
    if user.is_authenticated:
        logout(request)
    return redirect('categories_url')

def get_user_profile_page(request):
    user = request.user

    if user.is_authenticated:
        context = {"user": user}
        return render(request, 'first_app/user_profile.html', context)
    else:
        return redirect('home_url')

# -----------------------------------------------------------------------------------------

def get_register_page(request):
    if request.method == "POST":
        user_form = UserForm(request.POST)  
        profile_form = ProfileForm(request.POST)  

        # Проверяем есть ли уже пользователь с таким адресом почты.
        email = request.POST.get('email')
        if User.objects.filter(email=email).exists():
            messages.error(request, 'This email already registred on site.')
            return redirect('register_url')

        if User.objects.filter(username=request.POST.get('username')).exists():
            messages.error(request, 'This username already registred on site.')
            return redirect('register_url')
                
        if user_form.is_valid() and profile_form.is_valid():             

            new_user = user_form.save()   
            profile_test = Profile.objects.get(user=new_user) # Делаем сразу get() т.к. Profile уже создан автоматически после User.                
            profile_test.phone_number=profile_form.cleaned_data.get('phone_number','')
            profile_test.address=profile_form.cleaned_data.get('address', '')
            profile_test.save()            

            # EMAIL confirmation. ++++++++++++++++++++++++++++++            
            uidb64 = urlsafe_base64_encode(force_bytes(new_user.pk))
            domain = get_current_site(request).domain
            link = reverse('activate', kwargs={'uidb64': uidb64,
                                                'token': my_token_generator.make_token(new_user)})
            activate_url = 'http://' + domain + link

            email_body = "Hi " + new_user.username + ' Please use this link to verify your account\n' + activate_url + '\n'

            # Some debug stuff.
            email_body += f"""---DEBUG information ---
                            domain : {domain}
                            link : {link}
                            uidb64 : {uidb64} """ 

            email_subject = 'Activate your shop account.'
            to_email = user_form.cleaned_data.get('email')
            email = EmailMessage(email_subject, email_body, settings.EMAIL_HOST_USER, to=[to_email])
            email.send(fail_silently=False)

            # EMAIL confirmation END. ++++++++++++++++++++++++++++++
            username = user_form.cleaned_data.get('username')
            messages.success(request, 'Account was created for ' + str(username) + '\n Verify your email to activate it')
            return redirect('login_url')
        else:
            messages.error(request, 'Your data is incorrect')
            return redirect('register_url')

    elif request.method == "GET":
        user_form = UserForm()  
        profile_form = ProfileForm()      
    
    return render(request, 'first_app/registration.html', {'form': user_form, 'profile_form': profile_form} )

class VerificationView(views.View): # WHAAAAAAAAAAAAAAAAAAAAAAAT
    def get(self, request, uidb64, token):
        try:            
            uid = urlsafe_base64_decode(uidb64).decode()
            user = User.objects.get(pk=uid)
        except(TypeError, ValueError, OverflowError):
            user = None
            #messages.error(request, f'1) User is None\n Because uid : {uid}')
        
        if user is not None and my_token_generator.check_token(user, token):
            user.refresh_from_db()            
            user.profile.email_is_verifyed = True

            user.save()            
            messages.info(request, 'Your account has been activated successfully!')
            return redirect('login_url')
        else:
            messages.info(request, f'Activation link is invalid or has been activated')        
            #messages.error(request, f'2) check_token is bad\n Because bool : {my_token_generator.check_token(user, token)}')
            return redirect('login_url')

def set_balance(request):
    user = User.objects.get(username=request.user.username)    
    if user.is_authenticated:
        try:
            suc_message = user.wallet.set_balance(500)                       
            messages.success(request, suc_message)
        except Exception as e:
            messages.error(request, str(e))

    return redirect('user_profile_url')

def buy_product(request, slug):
    product = Product.objects.get(slug=slug)  
    user = User.objects.get(username=request.user.username)

    if user.is_authenticated:
        try:
            suc_message = user.profile.buy_product(product=product)                
            messages.success(request, suc_message)
        except Exception as e:
            messages.error(request, str(e))
    context = {'product': product}
    return render(request, 'first_app/specific_product.html', context)
