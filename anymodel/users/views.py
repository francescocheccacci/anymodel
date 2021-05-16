from flask import render_template, url_for, flash, redirect, request, Blueprint, current_app
from flask_login import login_user, current_user, logout_user, login_required
from anymodel import db
import pandas as pd
import os
import rpy2.robjects as robjects
from rpy2.robjects import pandas2ri
from rpy2.robjects.conversion import localconverter
from bokeh.models import HoverTool, FactorRange, Plot, LinearAxis, Grid, Range1d
from bokeh.models.glyphs import VBar, Line, Scatter
from bokeh.plotting import figure
from bokeh.embed import components
from bokeh.models.sources import ColumnDataSource
from bokeh.models.tools import WheelZoomTool, ZoomInTool, ZoomOutTool, BoxZoomTool
from werkzeug.security import generate_password_hash,check_password_hash
from anymodel.models import User
from anymodel.users.forms import RegistrationForm, LoginForm, ResetPasswordRequestForm, ResetPasswordForm, UpdateUserEmailForm,UpdateUserUsernameForm, UpdateUserPictureForm, UpdateUserDatasetForm
from anymodel.users.email import send_password_reset_email
from anymodel.users.picture_handler import add_profile_pic
from anymodel.users.dataset_handler import add_dataset_name


users = Blueprint('users', __name__)

@users.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()

    if form.validate_on_submit():
        user = User(email=form.email.data.lower(),
                    username=form.username.data,
                    password=form.password.data)

        db.session.add(user)
        db.session.commit()
        flash('Thanks for registering! Now you can login!')
        return redirect(url_for('users.login'))
    return render_template('register.html', form=form)

@users.route('/login', methods=['GET', 'POST'])
def login():

    form = LoginForm()
    if form.validate_on_submit():
        # Grab the user from our User Models table
        user = User.query.filter_by(email=form.email.data.lower()).first()

        # Check that the user was supplied and the password is right
        # The verify_password method comes from the User object
        # https://stackoverflow.com/questions/2209755/python-operation-vs-is-not
        if user is not None:
            if user.check_password(form.password.data):
                #Log in the user

                login_user(user)
                flash('Logged in successfully.')

                # If a user was trying to visit a page that requires a login
                # flask saves that URL as 'next'.
                next = request.args.get('next')

                # So let's now check if that next exists, otherwise we'll go to
                # the welcome page.
                if next == None or not next[0]=='/':
                    next = url_for('users.account')

                return redirect(next)
            else:
                flash("Check your password")
        else:
            flash("Check your email")
    return render_template('login.html', form=form)


@users.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('users.account'))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            send_password_reset_email(user)
        flash('Check your email for the instructions to reset your password')
        return redirect(url_for('users.login'))
    return render_template('reset_password_request.html',
                           title='Reset Password', form=form)

@users.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('users.account'))
    user = User.verify_reset_password_token(token)
    if not user:
        return redirect(url_for('core.index'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Your password has been reset.')
        return redirect(url_for('users.login'))
    return render_template('reset_password.html', form=form)

@users.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('core.index'))


@users.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    profile_image = url_for('static', filename='profile_pics/' + current_user.profile_image)
    return render_template('account.html', current_user = current_user)

@users.route("/account/update-username", methods=['GET', 'POST'])
@login_required
def UpdateUserUsernameView():
    form = UpdateUserUsernameForm()
    if form.validate_on_submit():
        print(form)
        current_user.username = form.username.data
        db.session.commit()
        flash('Username Updated')
        return redirect(url_for('users.account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
    return render_template('UpdateUserUsername.html', form=form)

@users.route("/account/update-email", methods=['GET', 'POST'])
@login_required
def UpdateUserEmailView():
    form = UpdateUserEmailForm()
    if form.validate_on_submit():
        current_user.email = form.email.data
        db.session.commit()
        flash('Email Updated')
        return redirect(url_for('users.account'))
    elif request.method == 'GET':
        form.email.data = current_user.email
    return render_template('UpdateUserEmail.html', form=form)

@users.route("/account/update-pic", methods=['GET', 'POST'])
@login_required
def UpdateUserPictureView():
    form = UpdateUserPictureForm()
    if form.validate_on_submit():
        if form.picture.data:
            username = current_user.username
            pic = add_profile_pic(form.picture.data,username)
            current_user.profile_image = pic
        db.session.commit()
        flash('Profile picture Updated')
        return redirect(url_for('users.account'))
    profile_image = url_for('static', filename='profile_pics/' + current_user.profile_image)
    return render_template('UpdateUserPic.html', profile_image=profile_image, form=form)

@users.route("/account/update-dataset", methods=['GET', 'POST'])
@login_required
def UpdateUserDatasetView():
    form = UpdateUserDatasetForm()
    if form.validate_on_submit():
        if form.dataset.data:
            username = current_user.username
            dataset = add_dataset_name(form.dataset.data,username)
            current_user.dataset_name = dataset
        db.session.commit()
        flash('Dataset Updated')
        return redirect(url_for('users.account'))
    return render_template('UpdateUserDataset.html', form=form)

@users.route("/<username>")
def user_posts(username):
    page = request.args.get('page', 1, type=int)
    user = User.query.filter_by(username=username).first_or_404()
    blog_posts = BlogPost.query.filter_by(author=user).order_by(BlogPost.date.desc()).paginate(page=page, per_page=5)
    return render_template('user_blog_posts.html', blog_posts=blog_posts, user=user)

def get_filepath():
    if "account" in request.path:
        filepath = os.path.join(current_app.root_path, 'static\pdatasets', current_user.dataset_name)
    else:
        filepath = os.path.join(current_app.root_path, 'static\pdatasets', "sample_dataset.csv")
    return filepath

def get_inject():
    filepath = get_filepath()
    df = pd.read_csv(filepath)
    inject = df.to_html(classes='data', max_rows=40, max_cols=1000)
    return inject

@users.route("/sample-data/read-dataset", methods=['GET', 'POST'])
def sample_user_dataset():
    inject = get_inject()
    return render_template('ReadDataset.html', inject = inject)

@users.route("/account/read-dataset", methods=['GET', 'POST'])
@login_required
def user_dataset():
    inject = get_inject()
    return render_template('ReadDataset.html', inject = inject)

def get_columns():
    filepath = get_filepath()
    df = pd.read_csv(filepath)
    columns = list(df.columns.values)
    columns.remove("weight")
    columns.remove("observed")
    columns.remove("fitted")
    return columns

@users.route("/account/dataset-variables", methods=['GET', 'POST'])
@login_required
def dataset_variables():
    columns = get_columns()
    return render_template('DatasetVariables.html', columns = columns)

@users.route("/sample-data/dataset-variables", methods=['GET', 'POST'])
def sample_dataset_variables():
    columns = get_columns()
    return render_template('DatasetVariables.html', columns = columns)

def summary_dict(variable):
    filepath = get_filepath()
    df = pd.read_csv(filepath)
    pandas2ri.activate()
    robjects.globalenv["sample_dataset"] = pandas2ri.py2rpy(df)
    robjects.globalenv["grouping_variable"] = pandas2ri.py2rpy(df[str(variable)])
    robjects.r('''
        summary_function <- function(weight.Variable, response.Variable, grouping.Variable, fitted.Variable, decimals=4){
            ratio <- function(weight.Variable, response.Variable, grouping.Variable, decimals=4) {

              weight   <- tapply(weight.Variable, grouping.Variable, sum)
              response <- tapply(response.Variable, grouping.Variable, sum)
              ratio    <- round(response / weight, decimals)
              ratio[is.na(ratio)] <- 0
              return(
                ratio[order(names(ratio))]
              )
            }

            grouped.sum <- function(summed.Variable, grouping.Variable,decimals=2) {
              output   <- round(tapply(summed.Variable, grouping.Variable, sum),decimals)
              output[is.na(output)] <- 0
              return(
                output[order(names(output))]
              )
            }

            fit <- function(weight.Variable, fitted.Variable, grouping.Variable, decimals=4) {

              weight       <- tapply(weight.Variable, grouping.Variable, sum)
              response_hat <- tapply(fitted.Variable, grouping.Variable, sum)
              fit    <- round(response_hat / weight, decimals)
              fit[is.na(fit)] <- 0
              return(
                fit[order(names(fit))]
              )
            }
          rownames=row.names(ratio(weight.Variable, response.Variable, grouping.Variable, decimals=decimals))
          if (length(rownames)==0) {
              rownames=sample_dataset$total[1]
            }
          d = data.frame(
                         grouping  = rownames,
                         observed     = ratio(weight.Variable, response.Variable, grouping.Variable, decimals=decimals),
                         fitted       = fit(weight.Variable, fitted.Variable, grouping.Variable, decimals=decimals),
                         weight    = grouped.sum(weight.Variable, grouping.Variable, decimals=decimals),
                         row.names = c()
          )

          return(d)
        }
        variable_summary = summary_function(sample_dataset$weight, sample_dataset$observed, grouping_variable, sample_dataset$fitted)
        ''')
    variable_summary = robjects.globalenv['variable_summary']
    hover = create_hover_tool()
    hover2 = create_hover_tool2()
    plot = create_bar_chart(variable_summary, "", "grouping","weight", hover)
    plot2 = create_lines_chart(variable_summary, "", "grouping","observed","fitted", hover2)
    script, div = components(plot)
    script2, div2 = components(plot2)
    d = dict()
    d['script']=script
    d['script2']=script2
    d['div']=div
    d['div2']=div2
    d['variable_summary']=variable_summary
    return d

@users.route("/account/summary/<variable>", methods=['GET', 'POST'])
@login_required
def summary_variable(variable):
    d = summary_dict(variable)
    script=d['script']
    script2=d['script2']
    div=d['div']
    div2=d['div2']
    variable_summary=d['variable_summary']
    return render_template('PlotDatasetVariable.html', variable=variable, the_div=div, the_script=script, the_div2=div2, the_script2=script2, variable_summary = variable_summary.to_html())

@users.route("/sample-data/summary/<variable>", methods=['GET', 'POST'])
def sample_summary_variable(variable):
    d = summary_dict(variable)
    script=d['script']
    script2=d['script2']
    div=d['div']
    div2=d['div2']
    variable_summary=d['variable_summary']
    return render_template('PlotDatasetVariable.html', variable=variable, the_div=div, the_script=script, the_div2=div2, the_script2=script2, variable_summary = variable_summary.to_html())

def create_hover_tool():
    """Generates the HTML for the Bokeh's hover data tool on our graph."""
    hover_html = """
      <div>
        <span class="hover-tooltip">@weight weight</span>
      </div>
    """
    return HoverTool(tooltips=hover_html)

def create_hover_tool2():
    """Generates the HTML for the Bokeh's hover data tool on our graph."""
    hover_html = """
      <div>
        <span class="hover-tooltip">@observed observed</span>
      </div>
      <div>
        <span class="hover-tooltip">@fitted fitted</span>
      </div>
    """
    return HoverTool(tooltips=hover_html)

def create_bar_chart(data, title, x_name, y_name, hover_tool=None,
                     width=1100, height=400):
    """Creates a bar chart plot with the exact styling for the centcom
       dashboard. Pass in data as a dictionary, desired plot title,
       name of x axis, y axis and the hover tool HTML.
    """
    source = ColumnDataSource(data)
    xdr = FactorRange(factors=list(data[x_name]))
    ydr = Range1d(start=0,end=max(data[y_name])*1.05)

    tools = []
    if hover_tool:
        tools = [hover_tool,]

    plot = figure(title=title, x_range=xdr, y_range=ydr, plot_width=width,
                  plot_height=height,
                  min_border=0, toolbar_location="above", tools=tools,
                  outline_line_color="#666666")

    glyph = VBar(x=x_name, top=y_name, bottom=0, width=.8,
                 fill_color="#ffdf00")
    plot.add_glyph(source, glyph)
    plot.add_tools(WheelZoomTool())
    plot.add_tools(BoxZoomTool())
    plot.add_tools(ZoomOutTool())

    xaxis = LinearAxis()
    yaxis = LinearAxis()

    plot.add_layout(Grid(dimension=0, ticker=xaxis.ticker))
    plot.add_layout(Grid(dimension=1, ticker=yaxis.ticker))
    plot.toolbar.logo = None
    plot.min_border_top = 0
    plot.xgrid.grid_line_color = None
    plot.ygrid.grid_line_color = "#999999"
    plot.yaxis.axis_label = "Weight"
    plot.ygrid.grid_line_alpha = 0.1
    plot.xaxis.axis_label = "Grouping"
    plot.xaxis.major_label_orientation = 1
    return plot


def create_lines_chart(data, title, x_name, y_name, y2_name, hover_tool=None,
                      width=1100, height=400):
    """Creates a bar chart plot with the exact styling for the centcom
       dashboard. Pass in data as a dictionary, desired plot title,
       name of x axis, y axis and the hover tool HTML.
    """
    source = ColumnDataSource(data)
    xdr = FactorRange(factors=list(data[x_name]))
    ydr = Range1d(start=0,end=max(max(data[y_name]),max(data[y2_name]))*1.05)

    tools = []
    if hover_tool:
        tools = [hover_tool,]

    plot = figure(title=title, x_range=xdr, y_range=ydr, plot_width=width,
                  plot_height=height,
                  min_border=0, toolbar_location="above", tools=tools,
                  outline_line_color="#666666")

    glyph = Line(x=x_name, y=y_name, line_width=6, line_alpha=0.6,
                 line_color="#ffc0cb")
    glyph2 = Line(x=x_name, y=y2_name, line_width=6, line_alpha=0.6,
                 line_color="#013220")
    glyph1a = Scatter(x=x_name, y=y_name, size=7, marker = "square",
                 fill_color="#ffc0cb")
    glyph2a = Scatter(x=x_name, y=y2_name, size=7, marker = "square",
                 fill_color="#013220")

    plot.add_glyph(source, glyph)
    plot.add_glyph(source, glyph2)
    plot.add_glyph(source, glyph1a)
    plot.add_glyph(source, glyph2a)
    plot.add_tools(WheelZoomTool())
    plot.add_tools(BoxZoomTool())
    plot.add_tools(ZoomOutTool())

    xaxis = LinearAxis()
    yaxis = LinearAxis()

    plot.add_layout(Grid(dimension=0, ticker=xaxis.ticker))
    plot.add_layout(Grid(dimension=1, ticker=yaxis.ticker))
    plot.toolbar.logo = None
    plot.min_border_top = 0
    plot.xgrid.grid_line_color = None
    plot.ygrid.grid_line_color = "#999999"
    plot.yaxis.axis_label = "Observed and Fitted"
    plot.ygrid.grid_line_alpha = 0.1
    plot.xaxis.axis_label = ""
    plot.xaxis.major_label_orientation = 1
    return plot


@users.route("/sample-data", methods=['GET', 'POST'])
def sample_data():
    return render_template('sample_data.html')

@users.route("/sample-data-info", methods=['GET', 'POST'])
def sample_dataset_info():
    return render_template('sample_data_info.html')

@users.route("/sample-data-model", methods=['GET', 'POST'])
def sample_dataset_model():
    return render_template('sample_data_model.html')
