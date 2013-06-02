var async = require('async');
var enclient = require('./echonest.js')('ZMBQQBZ4DBZVTKOTB');

enclient.request('catalog/list', {}, function (error, catlist) {
  async.each(catlist.catalogs, function (catalog, callback) {
    enclient.request('catalog/delete', {id: catalog.id}, callback);
  }, function (err) {
    if (err) {
      console.log(err);
    } else {
      console.log("Deleted all catalogs.");
    }
  });
});
