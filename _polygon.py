import smtplib



s = smtplib.SMTP(host=HOST, port=587)
s.starttls()
s.login('noreply@push.money', 'bychevoz13')
message_template = open('api/templates/mail.html').read()


from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


# For each contact, send the email:
for name, email, amount in [
		['Ivan', 'ivan.d.kotelnikov@gmail.com', 1123],
		['Nik', 'callmyduck@gmail.com', 10.123]]:
          # create a message

    # add in the actual person name to the message template
    message = message_template.replace('{{name}}', name.title()).replace('{{amunt}}', str(amount))

    # setup the parameters of the message


    # add in the message body


    # send the message via the server set up earlier.
    s.send_message(msg)