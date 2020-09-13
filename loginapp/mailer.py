from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_text
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.urls import reverse_lazy
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib, ssl,datetime,json
from paypal.standard.models import ST_PP_COMPLETED

from irisk_admin.utils import *
from .tokens import account_activation_token

from irisk.settings import (
    MAILJET_API_KEY,
    MAILJET_API_SECRET_KEY
)
from mailjet_rest import Client
import os

def send_mail_aws(subject,body,to_email):
    import boto3
    from botocore.exceptions import ClientError

    # client = boto3.client('ses')
    region = "us-east-1"
    client = boto3.client(
        'ses',
        region_name=region,
        aws_access_key_id='AKIAID2JEM54AO3ICTCA',
        aws_secret_access_key='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'
    )

    response = client.send_templated_email(
    Source='hralgofins@gmail.com',
    Destination={
        'ToAddresses': [
            to_email,
        ],
    },
    ReplyToAddresses=[
        'hralgofins@gmail.com',
    ],
    ReturnPath='hralgofins@gmail.com',
    # SourceArn='string',
    # ReturnPathArn='string',
    # ConfigurationSetName='ConfigSet',.com"
    # subject = "test"
    # message = "hiii"
    Template='CommonTemplate',
    # TemplateArn='string',
    TemplateData=json.dumps({"subject":subject,"body":body})
    )
    print("Mail Response: {0} \n".format(str(to_email)),response)
    return response


def send_mail(receiver_email,subject,message):

    config = get_initial_email_config()
    smtp_server = config.get('EMAIL_HOST')
    port = config.get('EMAIL_PORT')  # For starttls
    sender_email = config.get('EMAIL_HOST_USER')
    password = config.get('EMAIL_HOST_PASSWORD')

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = receiver_email
    html_body = MIMEText(message, 'html')
    msg.attach(html_body)

    # Create a secure SSL context
    context = ssl.create_default_context()

    # Try to log in to server and send email
    try:
        server = smtplib.SMTP(smtp_server,port)
        server.ehlo() # Can be omitted
        server.starttls(context=context) # Secure the connection
        server.ehlo() # Can be omitted
        server.login(sender_email, password)
        # TODO: Send email here
        server.sendmail(sender_email, receiver_email, msg.as_string())

        print("mail sent")
    except Exception as e:
        # Print any error messages to stdout
        print("Mail error",e)
        print("Mail Config",config)
    finally:
        server.quit()

def send_mail_mailjet(subject, message, receiver_email,):
    api_key = MAILJET_API_KEY
    api_secret = MAILJET_API_SECRET_KEY
    mailjet = Client(auth=(api_key, api_secret), version='v3.1')
    data = {
        'Messages': [
            {
                "From": {
                    "Email": "sinclair@stclair.com.au",
                    "Name": "Sin Clair"
                },
                "To": [
                    {
                        "Email": receiver_email,
                        "Name": ""
                    }
                ],
                "Subject": subject,
                "HTMLPart": message,
            }
        ]
    }
    try:
        result = mailjet.send.create(data=data)
        print(result)
    except Exception as e:
        print("Mail Error: ", e)
    finally:
        print("Mail Sent")

def populate_context_and_send_mail(temp,to_email,context):
    body = str(temp.email_message).format(**context)
    body = render_to_string('irisk_admin/email_templates/common_temp.html',{'body':body})
    mail_subject = temp.email_subject
    # send_mail(to_email,mail_subject,body)
    # send_mail_aws(mail_subject,body,to_email)
    send_mail_mailjet(mail_subject, body, to_email)

def risk_limit_breach_mail(to_email,first_name,context):
    # body = str(temp.email_message).format(**context)
    body = render_to_string('theme_two/risk_limit_breach_mail.html',{'user':first_name,'data':context})
    mail_subject = "Your risk limit has breached."
    # send_mail(to_email,mail_subject,body)
    send_mail_aws(mail_subject,body,to_email)


def send_account_activation_mail(request,user,to_email):
    current_site = get_current_site(request)
    temp = get_register_template()
    uid = urlsafe_base64_encode(force_bytes(user.pk)).decode('utf-8')
    token = account_activation_token.make_token(user)

    link_dict = {
        'protocol':request.scheme,
        'domain':current_site.domain,
        'url':reverse_lazy('account:activate',kwargs={"uidb64":uid,"token":token})
    }
    context = {
        'user_first_name':user.get_full_name(),
        'username':user.username,
        'link':"<a href='{protocol}://{domain}{url}'>{protocol}://{domain}{url}</a>".format(**link_dict)
    }
    populate_context_and_send_mail(temp,to_email,context)

def send_account_activated_mail(user):
    temp = get_activation_template()
    context = {
        'user_first_name':user.get_full_name(),
    }
    populate_context_and_send_mail(temp,user.email,context)

def send_subscription_transaction_mail(order):
    user = order.user
    ipn = order.ipn
    context = {}
    if ipn.payment_status == ST_PP_COMPLETED:
        temp = get_subscription_success_template()
    else:
        temp = get_subscription_failed_template()
        context['payment_reason'] = ipn.pending_reason

    context['user_first_name'] = user.get_full_name()
    context['transaction_id'] = ipn.txn_id
    context['transaction_status'] = ipn.payment_status
    context['order_invoice'] = ipn.invoice
    context['transaction_amount'] = ipn.mc_gross
    context['order_amount'] = order.price_to_pay
    context['portfolio_slot'] = order.portfolio_slot
    context['iriskaware_report'] = order.iriskaware_report
    context['portfolio_report'] = order.portfolio_report
    context['risk_item_monitored'] = order.risk_item_monitored
    context['risk_control_chart'] = order.risk_control_chart

    populate_context_and_send_mail(temp,user.email,context)

def send_slot_renewable_transaction_mail(order):
    user = order.resource.user
    ipn = order.ipn
    context = {}
    if ipn.payment_status == ST_PP_COMPLETED:
        temp = get_slot_renewed_success_template()
    else:
        temp = get_slot_renewed_failed_template()
        context['payment_reason'] = ipn.pending_reason

    context['user_first_name'] = user.get_full_name()
    context['transaction_id'] = ipn.txn_id
    context['transaction_status'] = ipn.payment_status
    context['order_invoice'] = ipn.invoice
    context['transaction_amount'] = ipn.mc_gross
    context['order_amount'] = order.price_to_pay
    context['slot_type'] = order.resource.get_resource_type_display()

    populate_context_and_send_mail(temp,user.email,context)

def send_slot_renewable_notice_mail(resource):
    temp = get_subscription_renewable_notice_template()
    context = {}
    context['user_first_name'] = resource.user.get_full_name()
    context['is_allocated'] = resource.is_allocated
    context['slot_type'] = resource.get_resource_type_display()
    context['expiry'] = str(resource.expire_on)
    populate_context_and_send_mail(temp,resource.user.email,context)


def send_slot_expired_mail(resource):
    temp = get_resource_expired_template()
    context = {}
    context['user_first_name'] = resource.user.get_full_name()
    context['is_allocated'] = resource.is_allocated
    context['slot_type'] = resource.get_resource_type_display()
    context['expiry'] = str(resource.expire_on)
    populate_context_and_send_mail(temp,resource.user.email,context)

def send_contact_mail(mail_subject,body):
    config = get_initial_email_config()
    sender_email = config.get('EMAIL_HOST_USER')
    send_mail_aws(mail_subject,body,sender_email)
