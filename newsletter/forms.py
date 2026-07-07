from django import forms


class NewsletterSubscribeForm(forms.Form):
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(
            attrs={
                "placeholder": "Email",
                "class": (
                    "font-inter flex-1 min-w-0 bg-transparent border border-[#5b5b5b] "
                    "rounded-l-lg px-5 lg:px-6 py-6 lg:py-[30px] text-sm lg:text-base "
                    "placeholder-gray-500 focus:outline-none focus:border-white"
                ),
            }
        ),
    )
    g_recaptcha_response = forms.CharField(required=False, widget=forms.HiddenInput())
