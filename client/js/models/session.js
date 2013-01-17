define([
  'jquery',
  'backbone'
], function($, Backbone) {
  var SessionModel = Backbone.Model.extend({
    sync: function(method, model, options){
      if (method == 'create' || method == 'update') {
        localStorage.setItem('username', model.attributes.username)
        localStorage.setItem('password', model.attributes.password)
      } else if (method == 'read') {
        model.attributes.username = localStorage.getItem('username')
        model.attributes.password = localStorage.getItem('password')
      } else if (method == 'delete') {
        localStorage.setItem('username', '')
        localStorage.setItem('password', '')
      }
    },
    token: function() {
      // The authentication token
      return this.get('username') + ':' + this.get('password') 
    },
    logIn: function(username, password, callback) {
      sessionModel = this
      $.ajax({
        type: "POST",
        url: '/login',
        data: {
          username: username,
          password: password
        },
        dataType: 'json',
        success: function() {
          sessionModel.save({'username': username, 'password': password})
          callback()
        },
        error: function(jqXhr, textStatus, errorThrown) {
          alert('Incorrect username or password')
        }
      })
    },
    logOut: function(username, password) {
      this.save({'username': '', 'password': ''})
    },
    loggedIn: function() {
      return this.get('username') != '' && this.get('password') != ''
    }
  })
  return SessionModel
});

